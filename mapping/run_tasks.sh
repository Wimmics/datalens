#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

DB=database
TASK_COLLECTIONS=("tasks" "task_ids_api" "task_categories_api" "task_categories_models_api")

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")


for COLLECTION in "${TASK_COLLECTIONS[@]}"; do
   JSON_FILE="${COLLECTION}.json"
   if [ "$COLLECTION" = "task_ids_api" ] && [ -f "./mongo_import/tasks_ids_api.json" ]; then
      JSON_FILE="tasks_ids_api.json"
   fi

   if [ "$COLLECTION" = "task_categories_api" ] && [ -f "./mongo_import/tasks_categories_api.json" ]; then
      JSON_FILE="tasks_categories_api.json"
   fi

   if [ "$COLLECTION" = "task_categories_models_api" ] && [ -f "./mongo_import/tasks_categories_models_api.json" ]; then
      JSON_FILE="tasks_categories_models_api.json"
   fi

   echo "------------------------------------------------------------------------------"
   echo "Importing $JSON_FILE into collection '$COLLECTION'..."
   docker exec $MONGO_CONTAINER \
   mongoimport --drop --type=json -d $DB -c $COLLECTION /mongo_import/$JSON_FILE
   docker exec $MONGO_CONTAINER \
   mongo --quiet --eval "db.getSiblingDB('$DB').${COLLECTION}.createIndex({id:1})"
done

echo "------------------------------------------------------------------------------"
echo "Running multi-source mapping 'mapping_tasks.ttl'..."
docker exec -w /xr2rml_config $XR2RML_CONTAINER \
/bin/bash run_xr2rml_template.sh mapping_tasks.ttl tasks.ttl dataset1.0 tasks

echo "------------------------------------------------------------------------------"
echo "Done."
