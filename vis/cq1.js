
// Component configuration

const scatterplot = document.querySelector("#cq1-venus");
  scatterplot.sparqlEndpoint = "http://graph.i3s.unice.fr/repositories/datalens";
  scatterplot.sparqlQuery = `PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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
`;
  scatterplot.encoding = {
  "title": "Datasets for QA and subtasks",
  "nodes": {
    "field": [
      "datasetURI",
      "subtaskName"
    ],
   // "tooltip": { "fields": ["url", "subtaskName", "datasetName"] },
    "color": {
        "field": "type",
        "scale": {"range": "Category10" }, 
        "legend": { "display": false}   
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
      "source": "datasetURI",
      "target": "subtaskName"
    }
  },
  "interactions": {
    "nodeDetailsPanel": true
  },
};
  await scatterplot.launch();
