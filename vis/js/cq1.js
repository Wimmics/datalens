
// Component configuration
import sparqlQuery from "../../sparql-examples/cq1.rq?raw";

const venusChart = document.querySelector("#cq1-venus");
venusChart.sparqlQuery = sparqlQuery
venusChart.encoding = {
	"title": "Licensed ML Resources",
	"nodes": {
		source: {
			field: "datasetURI",
			labels: { field: "datasetName" }
		}, 
		target: {
			field: "licenseName"
		},
		"tooltip": {"title": "value"},
		"size": {
			metric: "degree",
			"scale": {
				"type": "linear",
				"range": [ 20, 55 ]
			},
			"legend": {
				"title": "Links Count",
				"position": "top-left",
				"display": true
			}
		}
	},
	"links": {
		type: "directional"
	}
};
await venusChart.launch();
