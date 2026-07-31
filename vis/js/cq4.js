
// Component configuration
import sparqlQuery from "../../sparql-examples/cq4.rq?raw";

const venusChart = document.querySelector("#cq4-venus");
venusChart.sparqlQuery = sparqlQuery

venusChart.encoding = {
	"title": "Which datasets and models are the most widely used or popular according to usage indicators?",
	"x": {
		"field": "likes",
		"axis": {
			"title": {
				"value": "Likes Count"
			}
		},
		"scale": { "type": "linear" }   
	},
	"y": {
		"field": "downloads",
		"axis": {
			"title": {
				"value": "Download Count"
			}
		},
		"scale": { "type": "log"}
	},
	"points": {
		"color": {field: "resourceType"}
	}
};

await venusChart.launch();
