#!/bin/bash

set -e

CONTAINER_NAME="virtuoso-datalens"
GRAPH_URI="http://example.org/data"
DATA_DIR="virtuoso-data"

echo "📁 Preparing data folder for Virtuoso..."
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR"/*
cp -r ../ontology/used-vocabularies/* "$DATA_DIR"/
cp ../ontology/mluo.ttl "$DATA_DIR"/

echo "🧼 Cleaning Turtle files (removing invalid XML characters)..."
for file in ../case-study/data/output/*.ttl; do
  filename=$(basename "$file")
  # Remove ASCII control characters except tab (0x09), LF (0x0A), and CR (0x0D)
  tr -d '\000-\010\013\014\016-\037' < "$file" > "$DATA_DIR/$filename"
done

echo "✅ Data copied to $DATA_DIR."

echo "🛑 Stopping existing Virtuoso container (if any)..."
docker-compose down

echo "🐳 Starting Virtuoso with Docker Compose..."
docker-compose up -d

echo "⏳ Waiting for Virtuoso SQL port (1111) to be ready..."

for i in {1..60}; do
  if docker exec "$CONTAINER_NAME" isql 1111 dba dba EXEC="EXIT;" >/dev/null 2>&1; then
    echo "✅ Virtuoso is ready."
    break
  fi
  echo "⏳ Waiting... ($i seconds)"
  sleep 1
done

echo "📥 Registering RDF files inside Virtuoso..."
ISQL_CMDS="ld_dir('/data', '*.ttl', '$GRAPH_URI');
rdf_loader_run();
checkpoint;
"

docker exec -i "$CONTAINER_NAME" isql 1111 dba dba VERBOSE=ON <<EOF
$ISQL_CMDS
EOF

echo "✅ RDF loaded into <$GRAPH_URI>."
echo "🌐 Access SPARQL endpoint at: http://localhost:8890/sparql"
