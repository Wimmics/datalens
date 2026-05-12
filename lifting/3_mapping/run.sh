#!/bin/bash
# Author: Anna BOBASHEVA, University Cote d'Azur, CNRS, Inria
#
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DB=database

# Prevent Git Bash / MSYS from converting Unix paths to Windows paths
export MSYS_NO_PATHCONV=1

die() {
   echo "ERROR: $*" >&2
   exit 1
}

if command -v python3 >/dev/null 2>&1; then
   PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
   PYTHON_BIN=python
else
   die "python/python3 not found"
fi

run_ttl_identifier_fixer() {
   local ttl_file="$1"
   (cd "${SCRIPT_DIR}" && "$PYTHON_BIN" mongo_import/processing/fix_identifiers.py "$ttl_file")
}

MONGO_CONTAINER=$(docker ps --format='{{.Names}}' | grep -m 1 "mongo-xr2rml" || true)
XR2RML_CONTAINER=$(docker ps --format='{{.Names}}' | grep -m 1 "morph-xr2rml" || true)

if [ -z "$MONGO_CONTAINER" ]; then
   die "mongo-xr2rml container not found."
fi

if [ -z "$XR2RML_CONTAINER" ]; then
   die "morph-xr2rml container not found."
fi

run_parser() {
   local parser_module="$1"
   local input_file="$2"
   local output_file="$3"

   (cd "${SCRIPT_DIR}/mongo_import" && "$PYTHON_BIN" -m "$parser_module" --input "$input_file" --output "$output_file")
}

process_single_batch() {
   local label="$1"
   local parser_script="$2"
   local batch_dir="$3"
   local collection="$4"
   local mapping_file="$5"
   local dataset_name="$6"
   local output_subdir="$7"
   local source_json="$8"
   local fix_action="${9:-}"

   local base_name
   local rel_input
   local rel_output
   local parsed_name
   local output_ttl
   local host_output_ttl

   base_name="$(basename "$source_json")"
   parsed_name="${base_name%.json}_parsed.json"
   output_ttl="${output_subdir}/${base_name%.json}.ttl"
   host_output_ttl="${SCRIPT_DIR}/xr2rml_output/${output_ttl}"
   rel_input="${batch_dir}/${base_name}"
   rel_output="${batch_dir}/${parsed_name}"

   if [ -f "$host_output_ttl" ]; then
      echo "Skipping $label batch '$base_name': output already contains '$output_ttl'"
      return 0
   fi

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

   if [ "${fix_action:-}" = "fix_identifiers" ]; then
      echo "Post-batch: running TTL identifier fixer for $output_ttl"
      run_ttl_identifier_fixer "xr2rml_output/${output_ttl}"
   fi
}

process_batches_alternately() {
   # Get list of dataset files
   local dataset_files=()
   local source_dir="${SCRIPT_DIR}/mongo_import/datasets_batches"
   
   if [ -d "$source_dir" ]; then
      while IFS= read -r -d '' file; do
         dataset_files+=("$file")
      done < <(find "$source_dir" -maxdepth 1 -type f -name '*.json' ! -name '*_parsed.json' -print0 | sort -z)
   fi

   # Get list of model files
   local model_files=()
   source_dir="${SCRIPT_DIR}/mongo_import/models_batches"
   
   if [ -d "$source_dir" ]; then
      while IFS= read -r -d '' file; do
         model_files+=("$file")
      done < <(find "$source_dir" -maxdepth 1 -type f -name '*.json' ! -name '*_parsed.json' -print0 | sort -z)
   fi

   if [ ${#dataset_files[@]} -eq 0 ] && [ ${#model_files[@]} -eq 0 ]; then
      echo "ERROR: no JSON batches found"
      exit 1
   fi

   docker exec "$XR2RML_CONTAINER" mkdir -p "/xr2rml_output/datasets"
   docker exec "$XR2RML_CONTAINER" mkdir -p "/xr2rml_output/models"

   echo "------------------------------------------------------------------------------"
   echo "Processing ${#dataset_files[@]} dataset batches and ${#model_files[@]} model batches alternately..."
   echo "------------------------------------------------------------------------------"

   # Determine maximum number of iterations
   local max_files=$((${#dataset_files[@]} > ${#model_files[@]} ? ${#dataset_files[@]} : ${#model_files[@]}))

   # Process alternately
   for ((i=0; i<max_files; i++)); do
      # # Process dataset file
      # if [ $i -lt ${#dataset_files[@]} ]; then
      #    echo "------------------------------------------------------------------------------"
      #    echo "Processing dataset batch ($((i+1))/${#dataset_files[@]})"
      #    echo "------------------------------------------------------------------------------"
      #    process_single_batch "dataset" "processing.dataset_parser" "datasets_batches" "datasets" "mapping_datasets.ttl" "dataset1.0" "datasets" "${dataset_files[$i]}" "fix_identifiers"
      # fi

      # Process model file
      if [ $i -lt ${#model_files[@]} ]; then
         echo "------------------------------------------------------------------------------"
         echo "Processing model batch ($((i+1))/${#model_files[@]})"
         echo "------------------------------------------------------------------------------"
         process_single_batch "model" "processing.model_parser" "models_batches" "models" "mapping_models.ttl" "model1.0" "models" "${model_files[$i]}" "fix_identifiers"
      fi
   done
}

# datasets and models - process alternately
process_batches_alternately

echo "------------------------------------------------------------------------------"
echo "Done."
