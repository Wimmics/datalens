
// Component configuration
import sparqlQuery from "../../sparql-examples/cq2.rq?raw";

const venusChart = document.querySelector("#cq2-venus");
venusChart.sparqlQuery = sparqlQuery
venusChart.encoding = {
	"title": "ML Task Ecossystem",
	"nodes": {
		"source": {
			"field": "resourceName",
			"labels": { "display": false, "field": "resourceName" },
			"color": { "value": "gray" },
				"size": {
				"metric": "degree",
				"scale": {
					"type": "linear",
					"range": [
						20,
						55
					]
				},
				"legend": {
					"display": false
				}
			}
		},
		"target": {
			"field": "relation",
			labels: { field: "relationName"},
			"color": { 
				"field": "pLabel",
				"scale": {"range": "Set3"},
				"legend": {
					"title": "Features",
					"position": "top-right"
				}
			},
			"size": {
				"metric": "degree",
				"scale": {
					"type": "linear",
					"range": [
						20,
						55
					]
				},
				"legend": {
					"display": false
				}
			}
		},
		
	},
	"links": {
		"type": "semantic",
		"relation": { "field": "pLabel"},
		"labels": { "display": false, "field": "pLabel" },
		"color": { "value": "#ccc" }    
	}
}

await venusChart.launch();
