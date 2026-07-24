# Datalens-based KG for Hugging Face ML Resources

This directory contains scripts for retrieving, processing, and lifting machine learning resource metadata from the Hugging Face Hub using the Datalens semantic model.

## Overview

### 1. Fetching

The [fechting](./fechting/) folder contains scripts to fetch metadata from the Hugging Face API and prepare it for batch processing.

- [fetch_hf.py](./fechting/fetch_hf.py): fetches dataset or model metadata from the Hugging Face Hub API and saves the result as JSON files in an `input` folder created on the fly. The script supports checkpointing, cursor-based resume, duplicate avoidance, and rate-limit retries.
- [split_input_batches.py](./fechting/split_input_batches.py): splits `input/datasets.json` and/or `input/models.json` into smaller JSON batches. By default, datasets are split into 8 batches and models into 24 batches, which makes the downstream lifting process easier to run and resume.

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
python kg/fechting/fetch_hf.py --kind dataset
python kg/fechting/fetch_hf.py --kind model
```

2. (Optional) Split fetched data into batches:

```sh
python kg/fechting/split_input_batches.py --kind both
```

You can also split only one resource type:

```sh
python kg/fechting/split_input_batches.py --kind datasets
python kg/fechting/split_input_batches.py --kind models
```

3. Prepare the XR2RML workspace:

- Copy the generated batch folders from `kg/input` into `xr2rml_docker/mongo_import`.
- Copy the [processing](./processing/) folder into `xr2rml_docker/mongo_import`.
- Copy [mapping_datasets.ttl](./lifting/mapping_datasets.ttl) and [mapping_models.ttl](./lifting/mapping_models.ttl) into `xr2rml_docker/xr2rml_config`.
- Copy [run.sh](./lifting/run.sh) to the root of `xr2rml_docker`.

4. Run the XR2RML lifting process:

```sh
cd xr2rml_docker
bash run.sh
```

5. Retrieve the generated `.ttl` files from `xr2rml_output/datasets` and `xr2rml_output/models`.

# Data lifting for other repositories

To adapt metadata coming from another repository, keep the same pipeline shape and adapt only the ingestion and normalization layer:

1. Add a fetch script for the new source.

   - Add a fetcher such as `fechting/fetch_hf.py` if the source is Hugging Face-like.
   - Save the raw metadata as JSON in `lifting/input`.

---

2. Normalize the raw records in `processing/`.

   - Add a parser such as `dataset_parser.py` or `model_parser.py`.
   - Map source fields to the common Datalens schema used by the XR2RML mappings.

     - For datasets :

       - Example

         - *metadata : parser field*
       - Metadata to parse

         - URI : dataset_hash16 (as a hash which means the 16 first digits of a hash generated by sha256)
         - identifier : id (as a string)
         - description : description (as a string)
         - creation date : created_at (as a string)
         - last update : last_modified (as a string)
         - download count : downloads (as a string)
         - likes count or equivalent : likes (as a string)
         - acces rights : private and gated (as boolean)
         - tags : tags (as a list of string)
       - External URIs to build

         - region : region_uris (as a list of URI)
         - languages : language_uris (as a list of URI)
         - license : license_uris (as a list of URI)
       - Metadata that need to be align with the Datalens thesaurus

         - size : size_categories (as a list of thesaurus concepts for Huging Face but it can be a string with the number of Mo, Go)
         - subtask : task_ids (as a list of thesaurus concepts)
         - task categories : task_categories (as a list of thesaurus concepts)
         - modality : modalities (as a list of thesaurus concepts)
         - libraries : thesaurus_libraries (as a list of thesaurus concepts)
       - RDF ressources

         - source datasets in the graph : source_dataset_hash16 (as a list of hash)
         - external source datasets : source_dataset_non_hf_instances[*].source_dataset_hash16 (as a list of hash)
           - identifier of the dataset : source_dataset_non_hf_instances[*].source_dataset_label (as a string)
         - creator : creator_hash16 (as a hash)
           - identifier of the creator : author (as a string)
         - distribution : distribution_hash16 (as a hash)
           - format : format (as a list of thesaurus concepts)
         - academic article : article_hash16 (as a hash)
           - identifier of the article : paperid (as a list of string)
           - doi : doi (as a list of string)
           - url of the article : paperurl (as a list of url)
         - annotations : annotation_hash16 (as a hash)
           - annotation method : annotations_creators (as a list of string)
           - linguistic method : annotations_creators (as a list of string)
     - For models :

       - Example

         - *metadata : parser field*
       - Metadata to parse

         - URI : model_hash16 (as a hash which means the 16 first digits of a hash generated by sha256)
         - identifier : id (as a string)
         - creation date : created_at (as a string)
         - download count: downloads (as a string)
         - likes count or equivalent : likes (as a string)
         - acces rights : private and gated (as boolean)
         - tags : tags (as a list of string)
       - External URIs to build

         - region : region_uris (as a list of URI)
         - languages : language_uris (as a list of URI)
         - license : license_uris (as a list of URI)
       - Metadata that need to align with the Datalens thesaurus

         - task categories : task_categories (as a list of thesaurus concepts)
         - modalities : modalities (as a list of thesaurus concepts)
         - libraries : thesaurus_libraries (as a list of thesaurus concepts)
       - RDF ressources

         - training datasets in the graph : datasets_hash16 (as a list of hash)
         - external training datasets : datasets_non_hf_instances[*].dataset_hash16 (as a list of hash)

           - identifier of the dataset : dataset_non_hf_instances[*].dataset_label (as a string)
         - source models in the graph : source_models[*].source_model_hash16 (as a list of hash)
         - external source models : source_models_non_hf_instances[*].source_model_hash16 (as a list of hash)

           - identifier of the dataset : source_models_non_hf_instances[*].model_label (as a string)
         - derivations : source_models[*].derivation_hash16 (as a list of hash)

           - source model : source_models[*].source_model_hash16 (as a list of hash)
           - transformation type of the source model : source_models[*].transformation_type (as a thesaurus concept)
         - model configuration : config_hash16 (as a hash)

           - model type : config.model_type (as a string)
           - model arcitecture : config.architectures (as a list of string)
         - creator : creator_hash16 (as a hash)

           - identifier of the creator : author (as a string)
         - distribution : distribution_hash16 (as a hash)

           - format : format (as a list of thesaurus concepts)
         - academic article : article_hash16 (as a hash)

           - identifier of the article : paperid (as a list of string)
           - doi : doi (as a list of string)
           - url of the article : paperurl (as a list of url)

- Keep the normalized field names stable so the Turtle mappings do not need to change for every source.

---

3. Adapt controlled vocabularies and fallback values when needed.

   - Update `processing/canonical_thesaurus.py` for tags, tasks, licenses, languages, regions, or other canonical values.
   - Use fallback instances for labels that do not belong to the internal thesaurus. (example : `fallback_model_libraries()` in `processing/canonical_thesaurus.py` for the model libraries absent of the thesaurus)

---

4. Update the XR2RML mappings only if the normalized schema changes.

   - The mappings in `lifting/mapping/` expect the normalized parser fields such as `id`, `created_at`, `downloads`, `likes`, `tags`.
   - You must change :
     - the constant template of the publisher (example: "http://ns.inria.fr/datalens/data/publisher/HuggingFace")
     - the template of the landing page (example: "https://huggingface.co/datasets/{$.id}")
   - If the source exposes useful extra entities, add a new TriplesMap.

---

5. Test the full flow on a small batch first.

   - Fetch a few records.
   - Prepare the XR2RML workspace like explained in Usage.
   - Run the parser and generate Turtle with `mapping/run.sh`.
   - Check that all triples are correct.

In practice, the main rule is: normalize source-specific metadata into the Datalens intermediate format first, then let XR2RML handle the RDF generation.
