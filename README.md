# Datalens: Semantic Model and Knowledge Graph for ML Resources

Datalens provides a semantic model, knowledge graph construction pipeline, SPARQL competency questions, and interactive visualizations for exploring machine learning resources such as datasets and models.

The project focuses on describing resources published on platforms such as Hugging Face, aligning their metadata with controlled vocabularies, and enabling semantic exploration of tasks, modalities, licenses, provenance links, and popularity indicators.

## Overview

Datalens provides an ontology and a thesaurus to:

- Model machine learning datasets and models as semantic resources
- Describe resources with tasks, subtasks, modalities, formats, libraries, licenses, languages, regions, and scholarly references
- Capture provenance relationships, including training-data links and model derivations
- Build an RDF knowledge graph from Hugging Face metadata
- Support competency-question analysis through SPARQL queries and Venus visualizations

The Datalens ontology namespace is `http://ns.inria.fr/datalens/ontology/`.

The Datalens thesaurus namespace is `http://ns.inria.fr/datalens/thesaurus/`.

The Datalens-based KG is publicly available through a SPARQL endpoint at: `http://graph.i3s.fr/repositories/datalens`.

## RDF Data Modeling

The [ontology](ontology) directory contains the semantic model:

- [datalens_o.ttl](ontology/datalens_o.ttl): OWL ontology for machine learning resources, including datasets, models, distributions, annotations, libraries, tasks, modalities, and provenance relationships.
- [datalens_th.ttl](ontology/datalens_th.ttl): SKOS thesaurus with controlled vocabularies for tasks, subtasks, modalities, formats, size categories, libraries, and transformation types.

See [ontology/README.md](ontology/README.md) for a summary of the main classes and concept schemes.

## Knowledge Graph Construction

The [kg](kg) directory contains the pipeline used to build the Datalens knowledge graph from Hugging Face metadata.

The pipeline:

- Fetches dataset and model metadata from the Hugging Face Hub API
- Splits large JSON collections into batches
- Normalizes tags and metadata fields
- Aligns raw metadata values with Datalens thesaurus concepts
- Generates stable identifiers for resources and related entities
- Lifts processed JSON metadata to RDF/Turtle with XR2RML mappings

See [kg/README.md](kg/README.md) for requirements and execution details.

## Expert Validation of SKOS thesaurus

To validate the ML task hierarchy, we conducted an expert evaluation with IT researchers and developers. 

See [expert-validation](./expert-validation/) for more details on the protocol and obtained results.

## Competency Questions and Visualizations

The [sparql-examples](sparql-examples) directory contains SPARQL implementations of the competency questions used to inspect the knowledge graph.

The current competency questions cover:

- Datasets supporting a given machine learning task
- Datasets supporting a task for a specific modality under constraints
- Provenance relationships between models, datasets, and derived resources
- Popularity indicators for datasets and models

The [vis](vis) directory contains a Vite-based dashboard that uses [Venus elements](https://github.com/Wimmics/venus) to visualize those competency questions. Each visualization loads its query from the matching `.rq` file in [sparql-examples](sparql-examples), keeping the SPARQL examples and the dashboard coherent.

To run the visualization dashboard:

```sh
cd vis
npm install
npm run dev
```

An interactive dashboard presenting the CQ visualizations is available [here](https://wimmics.github.io/datalens/).

## Directory Structure

```text
datalens/
├── ontology/              # OWL ontology and SKOS thesaurus
│   ├── datalens_o.ttl
│   ├── datalens_th.ttl
│   └── README.md
│
├── kg/                    # Knowledge graph construction pipeline
│   ├── fechting/          # Hugging Face metadata fetching and batching scripts
│   ├── processing/        # Metadata normalization and cleanup scripts
│   ├── lifting/           # XR2RML mappings and lifting orchestration
│   ├── requirements.txt
│   └── README.md
│
├── sparql-examples/       # Competency-question SPARQL queries
│   ├── cq1.rq
│   ├── cq2.rq
│   ├── cq3.rq
│   ├── cq4.rq
│   └── README.md
│
└── vis/                   # Venus dashboard for CQ visualizations
    ├── index.html
    ├── css/
    ├── js/
    └── package.json
```

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file.
