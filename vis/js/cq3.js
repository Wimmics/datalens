
// Component configuration
import sparqlQuery from "../../sparql-examples/cq3.rq?raw";

const venusChart = document.querySelector("#cq3-venus");

venusChart.sparqlQuery = sparqlQuery
	
venusChart.encoding = {
	"title": "Which and how existing ML resources are used to support the construction of other datasets and models?",
	"nodes": {
		source: {
			field: "model",
			color: { value: "orange" },
			labels: { display:true, field: "modelName" }
		},
		target: {
			field: "resource",
			labels: { display: true, field: "resourceName"},
			"color": {
				"field": "resourceType",
				"scale": {"range": "Category10" },
				"legend" : { "position": "top-right" }
			}
		},
		"size": {
			metric: "degree",
			"scale": {
				"type": "linear",
				"range": [ 20, 55 ]
			},
			"legend": {
				position: "top-right"
			}
		}
	},
	"links": {
		type: "semantic",
		relation: { field: "relationship"},
		color: {
			field: "relationship",
			scale: {
				range: "Set3"
			},
			legend: {
				position: "top-right"
			}
		},
		size: { value: 4}
	}
};
await venusChart.launch();
