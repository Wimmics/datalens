
// Component configuration
import sparqlQuery from "../../sparql-examples/cq4.rq?raw";

const scatterplot = document.querySelector("#cq4-venus");
  scatterplot.sparqlEndpoint = "https://[endpoint]/repositories/datalens";
  scatterplot.sparqlQuery = sparqlQuery;

  scatterplot.encoding = {
  "title": "ML Resources Popularity",
  "x": {
    "field": "likes",
    "axis": {
      "title": {
        "value": "Likes Count",
        "display": true
      }
    },
    "scale": { "type": "log" }   
  },
  "y": {
    "field": "downloads",
    "axis": {
      "title": {
        "value": "Download Count",
        "display": true
      }
    },
    "scale": { "type": "log"}
  },
  "points": {
    "display": true,
    "color": {
      "field": "modality",
      "legend": {
        "position": "top-right"
      }
    },
    "size": {
      "value": 4
    },
   
  }
};

  await scatterplot.launch();
