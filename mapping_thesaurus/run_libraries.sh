#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

set -euo pipefail

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONGO_IMPORT_DIR="${SCRIPT_DIR}/mongo_import"
XR2RML_CONFIG_DIR="${SCRIPT_DIR}/xr2rml_config"

DB=database
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")
MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")

if [ -z "$XR2RML_CONTAINER" ]; then
   echo "ERROR: morph-xr2rml container not found."
   exit 1
fi

if [ -z "$MONGO_CONTAINER" ]; then
   echo "ERROR: mongo-xr2rml container not found."
   exit 1
fi

REQUIRED_JSON=("libraries.json")

echo "------------------------------------------------------------------------------"
echo "Checking required JSON files in ${MONGO_IMPORT_DIR}..."
for JSON_FILE in "${REQUIRED_JSON[@]}"; do
   test -f "${MONGO_IMPORT_DIR}/${JSON_FILE}" || {
      echo "ERROR: Missing ${MONGO_IMPORT_DIR}/${JSON_FILE}"
      exit 1
   }
done

echo "Copying JSON sources to ${XR2RML_CONFIG_DIR}..."
for JSON_FILE in "${REQUIRED_JSON[@]}"; do
   cp "${MONGO_IMPORT_DIR}/${JSON_FILE}" "${XR2RML_CONFIG_DIR}/${JSON_FILE}"
done

echo "------------------------------------------------------------------------------"
echo "Importing JSON files into MongoDB (${DB})..."
docker exec "$MONGO_CONTAINER" mongoimport --drop --type=json -d "$DB" -c libraries "/mongo_import/libraries.json"

echo "------------------------------------------------------------------------------"
echo "Running mapping_libraries.ttl -> libraries.ttl"
docker exec -w /xr2rml_config "$XR2RML_CONTAINER" \
/bin/bash run_xr2rml_template.sh mapping_libraries.ttl libraries.ttl dataset1.0 libraries

echo "------------------------------------------------------------------------------"
echo "Done."
