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
for file in "$ROOT_DIR"/artifacts/kg/huggingface/*.ttl; do
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

echo "📥 Loading RDF files through Virtuoso HTTP Graph Store endpoint..."
ENCODED_GRAPH_URI=$(printf '%s' "$GRAPH_URI" | sed -e 's/:/%3A/g' -e 's/\//%2F/g' -e 's/#/%23/g')
ENDPOINT="http://localhost:8890/sparql-graph-crud-auth?graph-uri=$ENCODED_GRAPH_URI"

echo "🧹 Clearing target graph before import..."
curl -sS --fail --digest -u dba:dba -X DELETE "$ENDPOINT" >/dev/null || true

shopt -s nullglob
ttl_files=("$DATA_DIR"/*.ttl)
if [ ${#ttl_files[@]} -eq 0 ]; then
  echo "❌ No TTL files found in $DATA_DIR"
  exit 1
fi

for file in "${ttl_files[@]}"; do
  filename=$(basename "$file")
  echo "  • Uploading $filename"
  curl -sS --fail --digest -u dba:dba -X POST \
    -H "Content-Type: text/turtle" \
    --data-binary "@$file" \
    "$ENDPOINT" >/dev/null
done

echo "🔎 Verifying triple count in graph <$GRAPH_URI>..."
curl -sS -u dba:dba -G "http://localhost:8890/sparql" \
  --data-urlencode "query=SELECT (COUNT(*) AS ?triples) FROM <$GRAPH_URI> WHERE { ?s ?p ?o }" \
  --data-urlencode "format=text/csv"

echo "✅ RDF loaded into <$GRAPH_URI>."
echo "🌐 Access SPARQL endpoint at: http://localhost:8890/sparql"
