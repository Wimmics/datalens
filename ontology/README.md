# Datalens OWL Ontology

An OWL ontology designed to represent machine learning resources (datasets and models).

Refer to the [`datalens_o.ttl`](datalens_o.ttl) file for the complete ontology definition.

## MLResource

The `dlo:MLResource` class is the parent class representing any machine learning resource published on platforms like Hugging Face. It serves as the foundation for both datasets and models, enabling shared properties and relationships such as download counts, and connections to tasks and libraries.

- **Common Properties**: `dlo:downloadCount`, `dlo:likesCount`
- **Relationships**: Links to tasks, modalities, libraries, and scholarly articles via BIBO vocabulary
- **Subclasses**: `dlo:Dataset`, `dlo:Model`

## Datasets

The `dlo:Dataset` class extends both `dcat:Dataset` and `dlo:MLResource`, representing datasets published on machine learning platforms. Datasets are characterized by their modalities, formats, size categories, and annotations.

## Models

The `dlo:Model` class extends both `schema:SoftwareSourceCode` and `dlo:MLResource`, representing machine learning models. Models capture specific tasks, with relationships to training data, architectures, and transformations.

## Tasks

The `dlo:Task` and `dlo:SubTask` classes represent machine learning problems and their granular specializations.

## Relationships and Provenance

The ontology uses PROV-O foundations to establish provenance chains:
- **`dlo:wasTrainedOn`**: Models linked to training datasets
- **Transformations**: Model derivations tracked as provenance activities

## Integration with SKOS Thesaurus

The OWL ontology references concepts from the `datalens_th.ttl` SKOS thesaurus:
- Modality, Format, and Size Category concepts populate the ontology's controlled vocabulary
- Task hierarchies in the thesaurus provide semantic structure for `dlo:Task` and `dlo:SubTask` instances


# Datalens SKOS Thesaurus

A SKOS thesaurus providing controlled vocabularies to describe machine learning resources. The thesaurus enables standardized annotation and discovery by organizing concepts into concept schemes.

Refer to the [`datalens_th.ttl`](datalens_th.ttl) file for the complete thesaurus definition.

## Modality Scheme

The `datalens_th:ModalityScheme` organizes concepts representing types of data modalities used in machine learning contexts, such as `Text`, `Image`, `Audio`, `Video`, `Tabular`, `TimeSeries`, `3D`, and `Geospatial`.

## Format Scheme

The `datalens_th:FormatScheme` groups concepts for data serialization and storage formats, including `JSON`, `CSV`, `Parquet`, `Arrow`, `WebDataset`, `ImageFolder`, `AudioFolder`, and others.

## Size Category Scheme

The `datalens_th:DatasetSizeScheme` defines concepts for dataset magnitude based on record count ranges (e.g., `< 1K`, `1K - 10K`, `100K - 1M`, `> 1T`).

## Dataset Library Scheme

The `datalens_th:DatasetLibraryScheme` catalogs libraries and frameworks for dataset access and manipulation, such as `Pandas`, `Polars`, `Datasets`, `WebDataset`, `Dask`, `FiftyOne`, and others.

## Model Library Scheme

The `datalens_th:ModelLibraryScheme` organizes concepts for machine learning libraries and frameworks, including `PyTorch`, `Transformers`, `Scikit-learn`, `TensorFlow`, `JAX`, `Keras`, and many specialized libraries.

## Task Scheme

The `datalens_th:TaskScheme` provides hierarchical organization of machine learning tasks with two levels:

- **Task**: Broad task of machine learning (e.g., Text Classification, Text Generation, Object Detection)
- **Sub Tasks**: Specific task with `skos:broader` links to their parent categories (e.g., Sentiment Classification under Text Classification)
- **Task Examples**: Enriched with examples from Hugging Face metadata