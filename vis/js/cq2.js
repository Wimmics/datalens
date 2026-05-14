
// Component configuration
import sparqlQuery from "../../sparql-examples/cq2.rq?raw";

const scatterplot = document.querySelector("#cq2-venus");
  scatterplot.sparqlEndpoint = "https://[endpoint]/repositories/datalens";
  scatterplot.sparqlQuery = sparqlQuery;
  scatterplot.encoding = {
  "title": "Licensed datasets for QA across modalities",
  "nodes": {
    "field": [
      "datasetURI",
      "licenseName"
    ],
    "tooltip": {"title": "value"},
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
      "target": "licenseName"
    }
  },
  "interactions": {
    "nodeDetailsPanel": true
  },
};
  await scatterplot.launch();
