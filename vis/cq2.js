
// Component configuration

const scatterplot = document.querySelector("#cq2-venus");
  scatterplot.sparqlEndpoint = "http://graph.i3s.unice.fr/repositories/datalens";
  scatterplot.sparqlQuery = `PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
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

    bind (REPLACE(
  REPLACE(
    STR(?license),
    STR(spdx:),
    ""
  ),
  STR(cc:),
  ""
) as ?licenseName)
}
`;
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
