
// Component configuration
import sparqlQuery from "../../sparql-examples/cq1.rq?raw";

const scatterplot = document.querySelector("#cq1-venus");
  scatterplot.sparqlEndpoint = "https://graph.i3s.unice.fr/repositories/datalens";
  scatterplot.sparqlQuery = sparqlQuery;
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
