#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

DB=database
COLLECTIONS=("datasets")

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")


for COLLECTION in "${COLLECTIONS[@]}"; do
   JSON_FILE="${COLLECTION}.json"
   MAPPING_FILE="mapping_${COLLECTION}.ttl"
   OUTPUT_FILE="${COLLECTION}.ttl"
   DATASET_NAME="$COLLECTION"

   echo "------------------------------------------------------------------------------"
   echo "Importing $JSON_FILE into collection '$COLLECTION'..."
   docker exec $MONGO_CONTAINER \
   mongoimport --drop --type=json -d $DB -c $COLLECTION /mongo_import/$JSON_FILE
   docker exec $MONGO_CONTAINER \
   mongo --quiet --eval "db.getSiblingDB('$DB').${COLLECTION}.createIndex({id:1})"


   echo "Running mapping '$MAPPING_FILE' on collection '$COLLECTION'..."
   docker exec -w /xr2rml_config $XR2RML_CONTAINER \
   /bin/bash run_xr2rml_template.sh $MAPPING_FILE $OUTPUT_FILE dataset1.0 $COLLECTION

done

echo "------------------------------------------------------------------------------"
echo "Done."
