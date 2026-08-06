# Datalens-based KG for Kaggle ML Resources

This directory contains the scripts used to fetch, normalize, and lift machine learning metadata from Kaggle into the Datalens knowledge graph.

## Pipeline

### 1. Fetching

The [fetching](./fetching/) folder contains scripts that retrieve metadata from Kaggle’s Meta Kaggle dataset and prepare it for downstream processing.

- [kaggle_models_fetcher.py](./fetching/kaggle_models_fetcher.py): downloads the relevant Meta Kaggle tables and builds a flat table with one row per model variation, merging model-level metadata onto each variation.
- [kaggle_datasets_fetcher.py](./fetching/kaggle_datasets_fetcher.py): downloads the relevant Meta Kaggle tables for datasets and prepares a normalized dataset-oriented export.

### 2. Processing

The [processing](./processing/) folder contains scripts for normalizing and enriching Kaggle metadata before RDF lifting.

- [model_parser.py](./processing/model_parser.py): normalizes model metadata from Kaggle into the Datalens intermediate schema, including tags, libraries, tasks, modalities, licenses, provenance, and version-related information.
- [dataset_parser.py](./processing/dataset_parser.py): normalizes dataset metadata from Kaggle into the Datalens intermediate schema, including ownership, tags, licenses, and dataset-level metadata.
- [canonical_thesaurus.py](./processing/canonical_thesaurus.py), [parser_tools.py](./processing/parser_tools.py), [fix_identifiers.py](./processing/fix_identifiers.py): same files as in [kg/](../kg/)

### 3. Lifting

The [lifting](./lifting/) folder contains the XR2RML mappings used to transform the normalized Kaggle data into RDF/Turtle.

- [mapping_datasets.ttl](./lifting/mapping_datasets.ttl): XR2RML mapping rules for Kaggle dataset metadata.
- [mapping_models.ttl](./lifting/mapping_models.ttl): XR2RML mapping rules for Kaggle model metadata.

## Main differences compared with the Hugging Face pipeline

The Kaggle pipeline follows the same overall structure as the Hugging Face pipeline, but with a few important differences:

1. The source is not the Hugging Face Hub API, but the Meta Kaggle dataset.
2. The fetch step relies on Kaggle CSV tables rather than JSON records retrieved from an API.
3. The model pipeline is centered on model variations rather than on a single model record, because Kaggle separates model-level and variation-level metadata.
4. The processing step focuses on aligning Kaggle tags and metadata with the same Datalens thesaurus concepts used in the Hugging Face workflow.
5. The lifting step reuses the same RDF target schema, so the output remains compatible with the Datalens knowledge graph.

## Usage

1. Run the Kaggle fetchers:

```sh
python kaggle_kg/fetching/kaggle_models_fetcher.py
python kaggle_kg/fetching/kaggle_datasets_fetcher.py
```

2. Run the parsers to normalize the fetched data.
3. Use the XR2RML mappings in the [lifting](./lifting/) folder to generate RDF/Turtle output.

## Notes

The Kaggle workflow is intentionally aligned with the Hugging Face pipeline so that both sources can converge toward the same Datalens intermediate representation and RDF schema.

## Limitations and next steps

The Kaggle pipeline now reuses the same Datalens normalization and lifting logic as the Hugging Face workflow, but some Kaggle-specific gaps remain.

### Current status

The current fetchers and parsers already capture the main Kaggle metadata blocks needed for lifting, including:

- model and dataset identifiers;
- model variations and their associated metadata;
- tags and basic provenance information;
- core fields required to align with the Datalens RDF schema.

### Remaining work

The main improvements still needed for the Kaggle pipeline are:

- **Model derivation** : for the moment, the variation of a model are represented derivating from a "base model" that doesn't exist. It only contains a identifier, a description and a landing page. It represents the model that regroup all the variations on Kaggle. A better way to represent this could be to derived all the variations from the default variation but it is complicated to identify.
- **Variation-level enrichment**: some metadata is available only at the variation level and still needs to be fully propagated into the normalized output.
- **Tag normalization**: Kaggle tags should be mapped more consistently to the existing Datalens thesauri, especially for package, task, architecture, technique, and analysis.
- **Task hierarchy integration**: Kaggle task labels should be incorporated into the hierarchical task thesaurus without breaking the existing structure already used for Hugging Face.
- **Coverage refinement**: certain Kaggle-specific fields, such as source organization and source URL for variations, should be better standardized and exposed in the final RDF representation.
