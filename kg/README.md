# Datalens-based KG for Hugging Face ML Resources

This directory contains the scripts used to fetch, normalize, and lift machine learning metadata from the Hugging Face Hub into the Datalens knowledge graph.

## Pipeline

### 1. Fetching

The [fetching](./fetching/) folder contains scripts that retrieve metadata from the Hugging Face API and prepare it for batch processing.

- [fetch_hf.py](./fetching/fetch_hf.py): fetches dataset or model metadata from the Hugging Face Hub API and saves the result as JSON files in an input folder created on the fly. The script supports checkpointing, cursor-based resume, duplicate avoidance, and rate-limit retries.
- [split_input_batches.py](./fetching/split_input_batches.py): splits fetched datasets and/or models into smaller JSON batches. By default, datasets are split into 8 batches and models into 24 batches to make downstream lifting easier to run and resume.

### 2. Processing

The [processing](./processing/) folder contains scripts for normalizing, enriching, and cleaning metadata before and after RDF lifting.

For JSON files, before lifting:

- [dataset_parser.py](./processing/dataset_parser.py): normalizes Hugging Face dataset metadata, deduplicates tags, maps tags to Datalens thesaurus concepts, extracts language, region, license, task, subtask, modality, library, size, format, and paper metadata, and generates stable hash identifiers used by the XR2RML mappings.
- [model_parser.py](./processing/model_parser.py): normalizes Hugging Face model metadata, derives authors from model identifiers, deduplicates tags, maps tasks, modalities, libraries, formats, licenses, languages, and regions, extracts paper and dataset references, parses base-model derivation tags, and generates stable hash identifiers used by the XR2RML mappings.
- [canonical_thesaurus.py](./processing/canonical_thesaurus.py): aligns raw Hugging Face tag values with canonical Datalens thesaurus concepts for tasks, subtasks, modalities, formats, size categories, dataset libraries, model libraries, and transformation types.
- [parser_tools.py](./processing/parser_tools.py): provides shared parsing helpers for string and boolean normalization, tag deduplication, URI construction, language and region inference, license normalization, paper URL creation, fallback library handling, and stable hash generation.

For TTL files, after lifting:

- [fix_identifiers.py](./processing/fix_identifiers.py): post-processes generated Turtle files to keep `dcterms:identifier` values aligned with Hugging Face landing page identifiers. This preserves identifiers containing double underscores and prevents identifier mismatches that would hinder traceability.

### 3. Lifting

The [lifting](./lifting/) folder contains the XR2RML mappings and execution script used to lift the processed JSON metadata into RDF/Turtle.

- [mapping_datasets.ttl](./lifting/mapping_datasets.ttl): XR2RML mapping rules for dataset metadata. The mapping creates Datalens dataset resources and related entities such as distributions, creators, licenses, languages, regions, papers, tasks, subtasks, modalities, formats, and dataset libraries.
- [mapping_models.ttl](./lifting/mapping_models.ttl): XR2RML mapping rules for model metadata. The mapping creates Datalens model resources and related entities such as distributions, creators, licenses, languages, regions, papers, tasks, modalities, model libraries, training datasets, source models, and derivation relationships.
- [run.sh](./lifting/run.sh): orchestration script for the XR2RML Docker workspace. It processes dataset and model batches alternately, runs the JSON parsers, imports parsed batches into MongoDB, executes the XR2RML mappings, writes Turtle output to `xr2rml_output`, and runs the TTL identifier fixer.

## Requirements

See [requirements.txt](./requirements.txt) for the full list of Python dependencies.

Main requirements for the Datalens lifting pipeline:

- Python 3.7+
- `huggingface_hub`
- `tqdm`
- Docker
- XR2RML Docker environment with MongoDB and Morph-XR2RML containers. Available at [https://github.com/frmichel/morph-xr2rml](https://github.com/frmichel/morph-xr2rml).

## Installation

1. Create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
```

2. Install dependencies:

```sh
pip install -r kg/requirements.txt
```

## Usage

1. Fetch datasets and models from Hugging Face:

```sh
python kg/fetching/fetch_hf.py --kind dataset
python kg/fetching/fetch_hf.py --kind model
```

2. Optional: split fetched data into batches.

```sh
python kg/fetching/split_input_batches.py --kind both
```

You can also split only one resource type:

```sh
python kg/fetching/split_input_batches.py --kind datasets
python kg/fetching/split_input_batches.py --kind models
```

3. Prepare the XR2RML workspace:

- Copy the generated batch folders from `kg/fetching/db/input` into `xr2rml_docker/mongo_import`.
- Copy the [processing](./processing/) folder into `xr2rml_docker/mongo_import`.
- Copy [mapping_datasets.ttl](./lifting/mapping_datasets.ttl) and [mapping_models.ttl](./lifting/mapping_models.ttl) into `xr2rml_docker/xr2rml_config`.
- Copy [run.sh](./lifting/run.sh) to the root of `xr2rml_docker`.

4. Run the XR2RML lifting process:

```sh
cd xr2rml_docker
bash run.sh
```

5. Retrieve the generated `.ttl` files from `xr2rml_output/datasets` and `xr2rml_output/models`.

## Data lifting for other repositories

To adapt metadata coming from another repository, keep the same pipeline shape and adapt only the ingestion and normalization layer.

1. Add a fetch script for the new source.

- Add a fetcher such as `fetching/fetch_hf.py` if the source is Hugging Face-like.
- Save the raw metadata as JSON in the fetch stage input folder.

2. Normalize the raw records in `processing/`.

- Add a parser such as `dataset_parser.py` or `model_parser.py`.
- Map source fields to the common Datalens schema used by the XR2RML mappings.
- Keep the normalized field names stable so the Turtle mappings do not need to change for every source.

3. Adapt controlled vocabularies and fallback values when needed.

- Update `processing/canonical_thesaurus.py` for tags, tasks, licenses, languages, regions, or other canonical values.
- Use fallback instances for labels that do not belong to the internal thesaurus.

4. Update the XR2RML mappings only if the normalized schema changes.

- The mappings in `lifting/` expect normalized parser fields such as `id`, `created_at`, `downloads`, `likes`, and `tags`.
- Change the publisher template and the landing page template if the source changes.
- If the source exposes useful extra entities, add a new TriplesMap.

5. Test the full flow on a small batch first.

- Fetch a few records.
- Prepare the XR2RML workspace as explained in Usage.
- Run the parsers and generate Turtle with `lifting/run.sh`.
- Check that the resulting triples are correct.

In practice, the main rule is to normalize source-specific metadata into the Datalens intermediate format first, then let XR2RML handle RDF generation.

## Latest developments

The fetching, processing, and lifting scripts are aligned with the current Hugging Face metadata flow, and the README now reflects the actual `fetching/`, `processing/`, and `lifting/` layout.

The batch workflow documents the current staging area under `fetching/db/input`, so the XR2RML handoff stays consistent with the repository structure.
