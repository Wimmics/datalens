#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DB=database
COLLECTIONS=("datasets")

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")


for COLLECTION in "${COLLECTIONS[@]}"; do
   SOURCE_JSON="${SCRIPT_DIR}/mongo_import/${COLLECTION}.json"

   if [ ! -f "$SOURCE_JSON" ]; then
      echo "ERROR: source JSON not found: $SOURCE_JSON"
      exit 1
   fi

   PARSE_CMD=(
      "dataset_parser.py"
      --input "${COLLECTION}.json"
      --output "${COLLECTION}_parsed.json"
   )

   if command -v python3 >/dev/null 2>&1; then
      (cd "${SCRIPT_DIR}" && cd mongo_import && python3 "${PARSE_CMD[@]}")
   elif command -v python >/dev/null 2>&1; then
      (cd "${SCRIPT_DIR}" && cd mongo_import && python "${PARSE_CMD[@]}")
   else
      echo "ERROR: python/python3 not found, cannot parse datasets"
      exit 1
   fi

   JSON_FILE="${COLLECTION}_parsed.json"
   MAPPING_FILE="mapping_${COLLECTION}.ttl"
   OUTPUT_FILE="${COLLECTION}.ttl"

   echo "------------------------------------------------------------------------------"
   echo "Importing $JSON_FILE into collection '$COLLECTION'..."
   
   # Drop collection, import only the specific JSON file, and create index
   docker exec $MONGO_CONTAINER \
   bash -c "mongo --eval \"db.${COLLECTION}.drop()\" localhost/$DB && \
   mongoimport --type=json --jsonArray -d $DB -c $COLLECTION /mongo_import/$JSON_FILE && \
   mongo --eval \"db.${COLLECTION}.createIndex({id: 1})\" localhost/$DB --quiet && \
   mongo --eval \"db.${COLLECTION}.count()\" localhost/$DB --quiet"


   echo "Running mapping '$MAPPING_FILE' on collection '$COLLECTION'..."
   docker exec -w /xr2rml_config $XR2RML_CONTAINER \
   /bin/bash run_xr2rml_template.sh $MAPPING_FILE $OUTPUT_FILE dataset1.0 $COLLECTION

done

echo "------------------------------------------------------------------------------"
echo "Done."
