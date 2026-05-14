
// Component configuration
import sparqlQuery from "../../sparql-examples/cq3.rq?raw";

const scatterplot = document.querySelector("#cq3-venus");
  scatterplot.sparqlEndpoint = "https://[endpoint]/repositories/datalens";
  scatterplot.sparqlQuery = sparqlQuery;
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
