
// Component configuration

const scatterplot = document.querySelector("#cq4-venus");
  scatterplot.sparqlEndpoint = "http://graph.i3s.unice.fr/repositories/datalens";
  scatterplot.sparqlQuery = `
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
}  `;

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
