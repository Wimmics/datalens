# Datalens Data Lifting

This directory contains scripts for lifting Hugging Face datasets and models to the Datalens ontology format.

## Overview

### 1. fechting/fetch_hf.py
Fetches datasets or models metadata from Hugging Face Hub and saves JSON files in `lifting/input`.

### 2. processing/
Preprocesses and normalizes fetched JSON files:
- `dataset_parser.py` for datasets
- `model_parser.py` for models
- `canonical_thesaurus.py` for canonical tags/thesaurus values

Postprocess TTL files:
- `fix_identifiers.py` for fixing identifiers errors

### 3. mapping/run.sh
Runs the XR2RML mappings (`mapping_datasets.ttl`, `mapping_models.ttl`) with XR2RML Docker from the XR2RML tool to generate RDF/Turtle output.

## Requirements
See `requirements.txt` for the full list of dependencies. Main requirements for the Datalens pipeline:
- Python 3.7+
- huggingface_hub
- tqdm

## Installation

1. **Setup virtual environment**:
```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. **Install dependencies**:
```sh
pip install -r requirements.txt
```

## Usage

1. Fetch datasets and models:
```sh
python lifting/1_fechting/fetch_hf.py --kind dataset
python lifting/1_fechting/fetch_hf.py --kind model
```

2. (Optional) Split fetched data into batches:
```sh
python lifting/1_fechting/split_input_batches.py --input lifting/input/datasets.json --output lifting/input/batches
python lifting/1_fechting/split_input_batches.py --input lifting/input/models.json --output lifting/input/batches
```

3. Prepare the XR2RML workspace (using XR2RML Docker from the XR2RML tool):
- put batches and the folder `processing` in `xr2rml_docker/mongo_import`
- put mapping files (`mapping_datasets.ttl`, `mapping_models.ttl`) in `xr2rml_docker/xr2rml_config`
- put `run.sh` at the root of `xr2rml_docker`

4. Run XR2RML in bash:
```sh
cd xr2rml_docker
bash run.sh
```

5. Retrieve generated `.ttl` files from `xr2rml_output`.