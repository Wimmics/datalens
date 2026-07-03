# Implementation of Competency Questions

This directory contains SPARQL queries used to demonstrate the potential of the Datalens (DL) approach to support semantic discovery and exploration of machine learning (ML) resources using the DL-based Hugging Face KG. 

These queries are implemented via an interactive interface featuring VENUS-based visualizations in `vis/js`. 

### CQ 1: Which datasets support a given task for a particular data modality under specific constraints?

[cq1.rq](cq1.rq) retrieves licensed audio datasets for QA:

- Filters datasets by task and modality
- Retrieves dataset identifiers, descriptions, source URLs, and licenses
- Normalizes SPDX and Creative Commons license IRIs into license names for visualization

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX dlt: <http://[anonymous]/datalens/thesaurus/>
PREFIX dlo: <http://[anonymous]/datalens/ontology/>
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

### CQ 2: Which datasets, models, libraries, and publications constitute the ecosystem surrounding a given ML task?

[cq2.rq](cq2.rq) retrieves the ecosystem of resources associated with a given ML task:

- Filters resources by task and minimum download count
- Retrieves datasets, models, libraries, publications, and related resources
- Extracts semantic relationships (e.g., training data, provenance, modality, license) together with their human-readable labels for visualization

```sparql
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dlt: <http://[anonymous]/datalens/thesaurus/>
PREFIX dlo: <http://[anonymous]/datalens/ontology/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT *
WHERE {
    ?resource dlo:hasTask dlt:QuestionAnswering ;
    	dcterms:identifier ?resourceName ;
    	dlo:downloadCount ?downloads .
           
    VALUES ?p {
        dlo:hasLibrary
        dlo:hasAcademicArticle
        dcterms:license
        dlo:hasTask
        dlo:hasSubTask
        dlo:hasModality
        prov:wasDerivedFrom
        dlo:wasTrainedOn
    }

    ?resource ?p ?relation .
    { ?relation rdfs:label ?relationName }
    UNION
    { ?relation skos:prefLabel ?relationName }
    UNION
    { ?relation dcterms:identifier ?relationName }
    
    ?p rdfs:label ?pLabel .
    FILTER(LANGMATCHES(LANG(?pLabel), "en"))
    
    FILTER (?downloads > 10000)
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
PREFIX dlo: <http://[anonymous]/datalens/ontology/>
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
PREFIX dlo: <http://[anonymous]/datalens/ontology/>
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
http://[anonymous]/repositories/datalens
```

Use a SPARQL client, the RDF triplestore, or the visualizations in `vis/` to run and explore the results.
