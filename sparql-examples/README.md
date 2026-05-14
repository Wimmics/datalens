# Implementation of Competency Questions

This directory contains SPARQL queries that implement key competency questions (CQ) for exploring machine learning resources with the Datalens ontology.

The queries are used by the Venus visualizations in `vis/js`.

### CQ 1: Which datasets support a given task?

[cq1.rq](cq1.rq) retrieves datasets related to question answering and links them to their subtasks:

- Retrieves dataset identifiers, descriptions, and landing pages
- Selects datasets associated with the `QuestionAnswering` (QA) task
- Finds subtasks broader than QA by navigating the hierarchical SKOS thesaurus

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX : <http://example.org/datalens/data#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX dlt: <http://ns.inria.fr/datalens/thesaurus/>
PREFIX dlo: <http://ns.inria.fr/datalens/ontology/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT * WHERE {
    ?datasetURI a dlo:Dataset ;
    	dlo:hasTask dlt:QuestionAnswering ;
    	dc:identifier ?datasetName ;
    	dc:description ?description ;
    	dcat:landingPage ?url ;
    	dlo:hasSubTask ?subtask .
    
    OPTIONAL { ?subtask skos:prefLabel ?subtaskName .
    ?subtask skos:broader dlt:QuestionAnswering .}
}
```

### CQ 2: Which datasets support a given task for a particular data modality under specific constraints?

[cq2.rq](cq2.rq) retrieves licensed audio datasets for QA:

- Filters datasets by task and modality
- Retrieves dataset identifiers, descriptions, source URLs, and licenses
- Normalizes SPDX and Creative Commons license IRIs into license names for visualization

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX dlt: <http://ns.inria.fr/datalens/thesaurus/>
PREFIX dlo: <http://ns.inria.fr/datalens/ontology/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX cc: <http://creativecommons.org/licenses/>
PREFIX spdx: <https://spdx.org/licenses/>

SELECT * WHERE {
    # Filters
    ?datasetURI a dlo:Dataset ;
    	dlo:hasTask dlt:QuestionAnswering ;
    	dlo:hasModality dlt:Audio ;
    	dc:license ?license .
    
    # Descriptive information
    ?datasetURI	dc:identifier ?datasetName ;
    	dc:description ?description ;
    	dcat:landingPage ?sourceUrl .

    BIND (REPLACE(
        REPLACE(
            STR(?license),
            STR(spdx:),
            ""
        ),
        STR(cc:),
        ""
    ) as ?licenseName)
}
```

### CQ 3: Which and how existing ML resources are used to support the construction of other datasets and models?

[cq3.rq](cq3.rq) retrieves provenance relationships between popular models and related resources:

- Selects models with more than 10,000 downloads
- Retrieves model identifiers and landing pages
- Finds resources connected through derivation or training relationships
- Distinguishes related resources as models or datasets

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX dlo: <http://ns.inria.fr/datalens/ontology/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT * WHERE {

    ?model a dlo:Model ;
        dc:identifier ?modelName ;
        dcat:landingPage ?modelUrl ;
        ?rel ?resource ;
    	dlo:downloadCount ?downloads .
	
    VALUES ?rel {
        prov:wasDerivedFrom
        dlo:wasTrainedOn
    }
    
    ?rel rdfs:label ?relationship.
    ?resource dc:identifier ?resourceName ;
      a ?type .
    
    VALUES ?type {
        dlo:Model
        dlo:Dataset
    }
    
    ?type rdfs:label ?resourceType .
    
    FILTER (?downloads > 10000)
    
}
```

### CQ 4: Which datasets and models are the most widely used or popular according to usage indicators?

[cq4.rq](cq4.rq) retrieves popularity indicators for machine learning resources:

- Retrieves download and like counts
- Retrieves resource landing pages and modalities
- Groups resources by ontology resource type
- Filters out very low-download resources and very high-like outliers

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dlo: <http://ns.inria.fr/datalens/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT * WHERE {
    ?resource dlo:downloadCount ?downloads ;
    dlo:likesCount ?likes .

    ?resource dcat:landingPage ?url ;
      dlo:hasModality [ skos:prefLabel ?modality ] ;
    	a ?type .
    
    ?type rdfs:subClassOf dlo:Ressource ; rdfs:label ?resourceType .

    FILTER (?downloads > 100 && ?likes < 9000)
}
```

## Usage

These queries can be executed against the Datalens SPARQL endpoint:

```text
http://graph.i3s.unice.fr/repositories/datalens
```

Use a SPARQL client, RDF store interface, or the Venus visualizations in `vis/` to run and inspect the results.
