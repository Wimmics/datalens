
// Component configuration

const scatterplot = document.querySelector("#cq3-venus");
  scatterplot.sparqlEndpoint = "http://graph.i3s.unice.fr/repositories/datalens";
  scatterplot.sparqlQuery = `PREFIX dcat: <http://www.w3.org/ns/dcat#>
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
    
}`;
  scatterplot.encoding = {
  "title": "Provenance relationship between models and datasets.",
  "nodes": {
    "field": [
      "model",
      "resource"
    ],
    "tooltip": {"title": "value"},
    "color": {
        "field": "resourceType",
        "scale": {"range": "Category10" },
        "legend" : { "position": "top-right" }
    },
    "size": {
      "field": "links",
      "scale": {
        "type": "linear",
        "range": [ 20, 55 ]
      },
      "legend": {
        "title": "Links Count",
        "position": "top-left",
        "display": false
      }
    }
  },
  "links": {
    "field": {
      "source": "model",
      "target": "resource"
    },
    "color": {
        "field": "relationship",
        "scale": {"range": "Set1" },
        "legend" : { "position": "top-right" }
    },
    "width": {"value": 3}
  },
  "interactions": {
    "nodeDetailsPanel": true
  },
};
  await scatterplot.launch();
