#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DB=database
COLLECTIONS=("datasets")
EXTRA_COLLECTIONS=(
   "datasets_modalities"
   "datasets_subjects"
   "datasets_languages"
   "datasets_task_categories"
   "datasets_task_ids"
   "datasets_usage_tasks"
   "datasets_usage_task_categories"
)

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")


for COLLECTION in "${COLLECTIONS[@]}"; do
   SOURCE_JSON="${SCRIPT_DIR}/mongo_import/${COLLECTION}.json"
   PREPROCESSED_JSON="${SCRIPT_DIR}/mongo_import/${COLLECTION}_preprocessed.json"

   if [ ! -f "$SOURCE_JSON" ]; then
      echo "ERROR: source JSON not found: $SOURCE_JSON"
      exit 1
   fi

   if command -v python3 >/dev/null 2>&1; then
      python3 "${SCRIPT_DIR}/mongo_import/preprocess_datasets.py" --input "$SOURCE_JSON" --output "$PREPROCESSED_JSON"
   elif command -v python >/dev/null 2>&1; then
      python "${SCRIPT_DIR}/mongo_import/preprocess_datasets.py" --input "$SOURCE_JSON" --output "$PREPROCESSED_JSON"
   else
      echo "ERROR: python/python3 not found, cannot preprocess datasets"
      exit 1
   fi

   JSON_FILE="${COLLECTION}_preprocessed.json"
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

   for EXTRA_COLLECTION in "${EXTRA_COLLECTIONS[@]}"; do
      EXTRA_FILE="${SCRIPT_DIR}/mongo_import/${EXTRA_COLLECTION}.json"
      if [ ! -f "$EXTRA_FILE" ]; then
         echo "ERROR: exploded JSON not found: $EXTRA_FILE"
         exit 1
      fi

      echo "Importing ${EXTRA_COLLECTION}.json into collection '$EXTRA_COLLECTION'..."
      docker exec $MONGO_CONTAINER \
      bash -c "mongo --eval \"db.${EXTRA_COLLECTION}.drop()\" localhost/$DB && \
      mongoimport --type=json --jsonArray -d $DB -c $EXTRA_COLLECTION /mongo_import/${EXTRA_COLLECTION}.json && \
      mongo --eval \"db.${EXTRA_COLLECTION}.count()\" localhost/$DB --quiet"
   done


   echo "Running mapping '$MAPPING_FILE' on collection '$COLLECTION'..."
   docker exec -w /xr2rml_config $XR2RML_CONTAINER \
   /bin/bash run_xr2rml_template.sh $MAPPING_FILE $OUTPUT_FILE dataset1.0 $COLLECTION

done

echo "------------------------------------------------------------------------------"
echo "Done."
