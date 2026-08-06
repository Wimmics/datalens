# Datalens Ontology

The Datalens ontology suite models machine learning resources, their metadata, and the controlled vocabularies used to describe them.

## Files

- [`datalens_o.ttl`](datalens_o.ttl): OWL ontology for datasets, models, tasks, provenance, and resource-level properties.
- [`datalens_th.ttl`](datalens_th.ttl): SKOS thesaurus for modalities, data types, formats, sizes, libraries, and tasks.
- [`model_family_thesaurus.ttl`](model_family_thesaurus.ttl): SKOS thesaurus for model family names and architectural lineages.
- [`ontology.rdf`](ontology.rdf): RDF serialization of the ontology package.

## Datalens OWL Ontology

The OWL ontology defines `dlo:MLResource` as the shared parent class for machine learning resources published on platforms such as Hugging Face. It supports common popularity measures and links to tasks, modalities, libraries, scholarly articles, and provenance relations.

### MLResource

The `dlo:MLResource` class is the parent class for any machine learning resource.

- **Common properties**: `dlo:downloadCount`, `dlo:likeCount`, `dlo:viewCount`, `dlo:kernelCount`
- **Relationships**: tasks, subtasks, modalities, data types, libraries, and academic articles
- **Superclass**: `prov:Entity`

### Datasets

The `dlo:Dataset` class extends both `dcat:Dataset` and `dlo:MLResource`. It is used for datasets published on machine learning platforms and can be described with modalities, data types, size categories, multilinguality, and annotations.

### Models

The `dlo:Model` class extends both `schema:SoftwareSourceCode` and `dlo:MLResource`. It captures model-specific metadata such as tasks, training data, architectures, model families, and transformations.

### Tasks

The `dlo:Task` and `dlo:SubTask` classes represent machine learning problems and their more specific specializations.

### Relationships and Provenance

The ontology uses PROV-O to represent provenance chains and model derivations.

- `dlo:wasTrainedOn`: links models to training datasets
- transformation activities: track how models are derived or adapted

### Integration with SKOS Thesauri

The OWL ontology references concepts from the SKOS thesauri in this folder.

- `datalens_th.ttl` provides the controlled vocabulary for modalities, formats, size categories, libraries, and tasks
- `model_family_thesaurus.ttl` provides the controlled vocabulary for model families and architecture lineages

## Datalens SKOS Thesaurus

The SKOS thesaurus provides controlled vocabularies for describing machine learning resources in a standardized way.

### Modality Scheme

The `dlt:ModalityScheme` organizes data modality concepts such as `Text`, `Image`, `Audio`, `Video`, `Tabular`, `TimeSeries`, `3D`, and `Geospatial`.

### Data Type Scheme

The `dlt:DataTypeScheme` organizes data type concepts such as `Document`, `Geometry`, `Graph`, `Tabular`, `TimeSeries`, `3D`, and `Geospatial`.

### Format Scheme

The `dlt:FormatScheme` groups serialization and storage formats such as `JSON`, `CSV`, `Parquet`, `Arrow`, `WebDataset`, `ImageFolder`, and `AudioFolder`.

### Size Category Scheme

The `dlt:DatasetSizeScheme` defines dataset magnitude ranges based on record counts.

### Dataset Library Scheme

The `dlt:DatasetLibraryScheme` catalogs dataset access and manipulation libraries such as `Pandas`, `Polars`, `Datasets`, `WebDataset`, `Dask`, and `FiftyOne`.

### Model Library Scheme

The `dlt:ModelLibraryScheme` organizes machine learning libraries and frameworks such as `PyTorch`, `Transformers`, `Scikit-learn`, `TensorFlow`, `JAX`, and `Keras`.

### Task Scheme

The `dlt:TaskScheme` provides a hierarchical organization of machine learning tasks.

- **Task**: broad tasks such as text classification, text generation, and object detection
- **SubTask**: more specific tasks linked to their parent concepts through `skos:broader`
- **Task examples**: enriched with examples from Hugging Face metadata

## Model Family Thesaurus

The `model_family_thesaurus.ttl` file extends the thesaurus layer with a controlled vocabulary for model families and related architectural groupings.

## Limitations and next steps

The thesauri derived from Hugging Face metadata are now synchronized and up to date.

For Kaggle, we can exploit **eight tag categories**: architecture, modality, audience, package, subject, task, technique, and analysis.

The current parsers already retrieve:

- all tags that are already covered by the Hugging Face thesauri;
- the Kaggle tags belonging to the **modality**, **audience**, and **subject** categories.

### Current coverage

- **Modality** and **audience** thesauri are already complete.
- The **subject** thesaurus still needs additional definitions.

### Remaining work

For the following categories, the tags are either reused from the existing Hugging Face thesauri or left as free tags for now:

- **Package**: we still need to filter the tags to keep only those related to machine learning and add them to the library thesaurus.
- **Task**: the task thesaurus is hierarchical, so Kaggle task tags still need to be integrated into this hierarchy. A first draft is available in `task_hierarchy.ttll`, but the definitions generated by ChatGPT still need to be reviewed and validated. The hierarchy is based on the generated definitions and the task names, since Kaggle does not provide more detailed information. The goal is to preserve the structure already built for Hugging Face tasks.
- **Architecture, technique, and analysis**: these tags are not yet properly categorized and may need to be distributed across multiple thesauri, including the model family thesaurus.
