#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DB=database

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep "mongo-xr2rml")
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep "morph-xr2rml")

if [ -z "$MONGO_CONTAINER" ]; then
   echo "ERROR: mongo-xr2rml container not found."
   exit 1
fi

if [ -z "$XR2RML_CONTAINER" ]; then
   echo "ERROR: morph-xr2rml container not found."
   exit 1
fi

run_parser() {
   local parser_script="$1"
   local input_file="$2"
   local output_file="$3"

   local parse_cmd=(
      "$parser_script"
      --input "$input_file"
      --output "$output_file"
   )

   if command -v python3 >/dev/null 2>&1; then
      (cd "${SCRIPT_DIR}/mongo_import" && python3 "${parse_cmd[@]}")
   elif command -v python >/dev/null 2>&1; then
      (cd "${SCRIPT_DIR}/mongo_import" && python "${parse_cmd[@]}")
   else
      echo "ERROR: python/python3 not found, cannot parse JSON batches"
      exit 1
   fi
}

process_batches() {
   local label="$1"
   local parser_script="$2"
   local batch_dir="$3"
   local collection="$4"
   local mapping_file="$5"
   local dataset_name="$6"
   local output_subdir="$7"

   local source_dir="${SCRIPT_DIR}/mongo_import/${batch_dir}"

   if [ ! -d "$source_dir" ]; then
      echo "ERROR: batch directory not found: $source_dir"
      exit 1
   fi

   local batch_files=()
   while IFS= read -r -d '' file; do
      batch_files+=("$file")
   done < <(find "$source_dir" -maxdepth 1 -type f -name '*.json' ! -name '*_parsed.json' -print0 | sort -z)

   if [ ${#batch_files[@]} -eq 0 ]; then
      echo "ERROR: no JSON batch found in $source_dir"
      exit 1
   fi

   echo "------------------------------------------------------------------------------"
    echo "Processing ${#batch_files[@]} ${label} batches from '$batch_dir'..."

   docker exec "$XR2RML_CONTAINER" mkdir -p "/xr2rml_output/${output_subdir}"

   for source_json in "${batch_files[@]}"; do
      local base_name
      local rel_input
      local rel_output
      local parsed_name
      local output_ttl

      base_name="$(basename "$source_json")"
      parsed_name="${base_name%.json}_parsed.json"
      output_ttl="${output_subdir}/${base_name%.json}.ttl"
      rel_input="${batch_dir}/${base_name}"
      rel_output="${batch_dir}/${parsed_name}"

      echo "------------------------------------------------------------------------------"
      echo "Batch: $base_name"

      run_parser "$parser_script" "$rel_input" "$rel_output"

      docker exec "$MONGO_CONTAINER" bash -c "mongo --eval \"db.${collection}.drop()\" localhost/$DB"

      docker exec "$MONGO_CONTAINER" \
      mongoimport --type=json --jsonArray -d "$DB" -c "$collection" "/mongo_import/${rel_output}"

      docker exec "$MONGO_CONTAINER" \
      bash -c "mongo --eval \"db.${collection}.createIndex({id: 1})\" localhost/$DB --quiet && \
      mongo --eval \"db.${collection}.count()\" localhost/$DB --quiet"

      echo "Running mapping '$mapping_file' -> '$output_ttl' on collection '$collection'..."
      docker exec -w /xr2rml_config "$XR2RML_CONTAINER" \
      /bin/bash run_xr2rml_template.sh "$mapping_file" "$output_ttl" "$dataset_name" "$collection"
   done
}

process_batches "dataset" "dataset_parser.py" "datasets_batches" "datasets" "mapping_datasets.ttl" "dataset1.0" "datasets"
process_batches "model" "model_parser.py" "models_batches" "models" "mapping_models.ttl" "model1.0" "models"

echo "------------------------------------------------------------------------------"
echo "Done."
