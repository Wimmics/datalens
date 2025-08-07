#!/bin/bash

set -e  # Exit if any command fails

echo "🔧 Preparing folders for Corese..."

# Clean and create the data folder
mkdir -p corese-data
rm -rf corese-data/*
cp -r ../case-study/data/output/* corese-data/
cp -r ../ontology/used-vocabularies/* corese-data/
cp ../ontology/mluo.ttl corese-data/
echo "✅ corese-data/ ready."

# Clean and create empty config folder
mkdir -p config
rm -rf config/*
echo "✅ config/ folder created and empty."

# Clean and create empty log folder
mkdir -p log
rm -rf log/*
echo "✅ log/ folder created and empty."

echo "🐳 Starting Docker Compose (detached)..."
docker-compose up -d

# Wait some time for container to initialize (adjust seconds as needed)
echo "⏳ Waiting 15 seconds for container initialization..."
sleep 15

# Restart the container
echo "🔄 Restarting the Corese container..."
docker-compose restart

echo "✅ Container restarted."

echo "ℹ️ The container is running detached. To stop it, run:"
echo "    docker-compose down"

# Optionally clean up after user manually stops container
# Uncomment the following lines if you want auto-clean on exit:
# echo "🧹 Cleaning up temporary folders..."
# rm -rf corese-data config log
# echo "✅ All temporary folders removed."
echo "🚀 Corese server is ready and running!"
