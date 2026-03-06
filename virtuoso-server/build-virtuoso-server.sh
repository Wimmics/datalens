#!/bin/bash

set -e

CONTAINER_NAME="virtuoso-datalens"
GRAPH_URI="http://example.org/data"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$SCRIPT_DIR/virtuoso-data"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "❌ Neither 'docker compose' nor 'docker-compose' was found."
  exit 1
fi

echo "📁 Preparing data folder for Virtuoso..."
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR"/*
cp -r "$ROOT_DIR/ontology/used-vocabularies"/* "$DATA_DIR"/
cp "$ROOT_DIR/ontology/mluo.ttl" "$DATA_DIR"/

echo "🧼 Cleaning Turtle files (removing invalid XML characters)..."
for file in "$ROOT_DIR"/artifacts/kg/huggingface_new_new/*.ttl; do
  filename=$(basename "$file")
  # Remove ASCII control characters except tab (0x09), LF (0x0A), and CR (0x0D)
  tr -d '\000-\010\013\014\016-\037' < "$file" > "$DATA_DIR/$filename"
done

echo "✅ Data copied to $DATA_DIR."

cd "$SCRIPT_DIR"

echo "🛑 Stopping existing Virtuoso container (if any)..."
$COMPOSE_CMD down

echo "🐳 Starting Virtuoso with Docker Compose..."
up_timed_out=false
if command -v timeout >/dev/null 2>&1; then
  if ! timeout 20s $COMPOSE_CMD up -d; then
    compose_status=$?
    if [ $compose_status -eq 124 ]; then
      up_timed_out=true
      echo "⚠️ 'docker compose up -d' timed out after 180s. Checking container state anyway..."
    else
      echo "❌ Docker Compose failed to start Virtuoso (exit code: $compose_status)."
      exit $compose_status
    fi
  fi
else
  $COMPOSE_CMD up -d
fi

container_running=false
for i in {1..30}; do
  state=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || true)
  if [ "$state" = "true" ]; then
    container_running=true
    break
  fi
  sleep 1
done

if [ "$container_running" != true ]; then
  echo "❌ Virtuoso container is not running after compose startup."
  echo "📋 Recent container logs:"
  docker logs --tail 120 "$CONTAINER_NAME" || true
  exit 1
fi

echo "🔧 Ensuring Virtuoso allows '/data' for bulk loading..."
if ! docker exec "$CONTAINER_NAME" sh -lc "grep -Eq '^DirsAllowed[[:space:]]*=.*/data' /database/virtuoso.ini"; then
  if ! docker exec "$CONTAINER_NAME" sh -lc "sed -i -E 's|^DirsAllowed[[:space:]]*=.*$|DirsAllowed              = ., ../vad, /usr/share/proj, /data|' /database/virtuoso.ini"; then
    echo "❌ Could not update DirsAllowed in /database/virtuoso.ini"
    exit 1
  fi
  echo "♻️ Restarting Virtuoso to apply DirsAllowed change..."
  docker restart "$CONTAINER_NAME" >/dev/null
fi

if [ "$up_timed_out" = true ]; then
  echo "✅ Container is running despite compose timeout. Continuing..."
fi

echo "⏳ Waiting for Virtuoso SPARQL endpoint (8890) to be ready..."

SPARQL_PING_URL="http://localhost:8890/sparql"
is_ready=false
for i in {1..120}; do
  if curl -sS --max-time 3 -u dba:dba -G "$SPARQL_PING_URL" \
    --data-urlencode "query=ASK { ?s ?p ?o }" \
    --data-urlencode "format=text/plain" >/dev/null 2>&1; then
    is_ready=true
    echo "✅ Virtuoso is ready."
    break
  fi
  echo "⏳ Waiting... ($i/120)"
  sleep 1
done

if [ "$is_ready" != true ]; then
  echo "❌ Virtuoso did not become ready in time."
  echo "📋 Recent container logs:"
  docker logs --tail 80 "$CONTAINER_NAME" || true
  exit 1
fi

echo "📥 Loading RDF files through Virtuoso bulk loader (isql + ld_dir)..."

shopt -s nullglob
ttl_files=("$DATA_DIR"/*.ttl)
if [ ${#ttl_files[@]} -eq 0 ]; then
  echo "❌ No TTL files found in $DATA_DIR"
  exit 1
fi

SQL_FILE="$SCRIPT_DIR/load_virtuoso.sql"
GRAPH_URI_SQL=${GRAPH_URI//\'/\'\'}

echo "🧹 Preparing SQL import plan..."
{
  echo "SET BLOBS ON;"
  echo "SPARQL CLEAR GRAPH <${GRAPH_URI}>;"
  echo "DELETE FROM DB.DBA.LOAD_LIST WHERE ll_graph = '${GRAPH_URI_SQL}';"
} > "$SQL_FILE"

for file in "${ttl_files[@]}"; do
  filename=$(basename "$file")
  echo "  • Queueing $filename"
  echo "ld_dir('/data', '${filename}', '${GRAPH_URI_SQL}');" >> "$SQL_FILE"
done

{
  echo "rdf_loader_run();"
  echo "checkpoint;"
} >> "$SQL_FILE"

echo "🚚 Copying SQL plan into container..."
docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/load_virtuoso.sql"

echo "⚙️ Running bulk RDF import inside Virtuoso..."
if ! docker exec "$CONTAINER_NAME" sh -lc "isql 1111 dba dba /tmp/load_virtuoso.sql"; then
  echo "❌ Bulk RDF import failed."
  docker exec "$CONTAINER_NAME" sh -lc "rm -f /tmp/load_virtuoso.sql" || true
  rm -f "$SQL_FILE"
  exit 1
fi

docker exec "$CONTAINER_NAME" sh -lc "rm -f /tmp/load_virtuoso.sql" || true
rm -f "$SQL_FILE"

for file in "${ttl_files[@]}"; do
  filename=$(basename "$file")
  echo "  • Loaded $filename"
done

echo "🔎 Verifying triple count in graph <$GRAPH_URI>..."
curl -sS -u dba:dba -G "http://localhost:8890/sparql" \
  --data-urlencode "query=SELECT (COUNT(*) AS ?triples) FROM <$GRAPH_URI> WHERE { ?s ?p ?o }" \
  --data-urlencode "format=text/csv"

echo "✅ RDF loaded into <$GRAPH_URI>."
echo "🌐 Access SPARQL endpoint at: http://localhost:8890/sparql"
