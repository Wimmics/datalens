import interactiveCQ1 from "../interactive-queries/cq1.rq?raw";
import interactiveCQ2 from "../interactive-queries/cq2.rq?raw";
import interactiveCQ3 from "../interactive-queries/cq3.rq?raw";
import interactiveCQ4 from "../interactive-queries/cq4.rq?raw";

import modalities from "../data/filters/modalities.json?raw"
import tasks from "../data/filters/tasks.json?raw"
import types from "../data/filters/resource-types.json?raw"

import * as d3 from "d3"

const queries = {
    cq1: interactiveCQ1,
    cq2: interactiveCQ2,
    cq3: interactiveCQ3,
    cq4: interactiveCQ4
}

export function queryResolver(cq, options = {}) {
    let query = queries[cq]

    for (let key of Object.keys(options)) {
        if (!options[key]) continue

        let value = options[key].replace("http://[anonymous]/datalens/ontology/", "dlo:")
            .replace("http://[anonymous]/datalens/thesaurus/", "dlt:")

        query = query.replace(`$${key}`, value)
    }

    return query
}

const defaults = {
    cq1: {
        "resource-type": "http://[anonymous]/datalens/ontology/Dataset",
        task: "http://[anonymous]/datalens/thesaurus/QuestionAnswering",
        modality: "http://[anonymous]/datalens/thesaurus/Audio"
    },
    cq2: {
        task: "http://[anonymous]/datalens/thesaurus/QuestionAnswering" 
    },
    cq3: {
        "resource-type": "http://[anonymous]/datalens/ontology/Model",
        modality: "http://[anonymous]/datalens/thesaurus/Audio"
    },
    cq4:{
        modality: "http://[anonymous]/datalens/thesaurus/Audio"
    }
}

const selectedValues = { ...defaults} // initialize selected values with defaults

const filterData = {
    "resource-type": JSON.parse(types)?.results.bindings,
    modality: JSON.parse(modalities)?.results.bindings,
    task: JSON.parse(tasks)?.results.bindings
}

export function setFilters(){
    for (const cq of ["cq1", "cq2", "cq3", "cq4"]) {
        for (const filterKey of Object.keys(filterData)) {
            
            const select = d3.select(`#${cq}-${filterKey}`)
            if (select.empty()) continue

            select.selectAll("option")
                .data(filterData[filterKey])
                .enter()
                .append("option")
                .attr("value", d => d.value.value)
                .text(d => d.label.value)

            select.property("value", defaults[cq][filterKey])
                .attr("data-filter", filterKey)
                .attr("data-query", cq)
                .on("change", async function(d){
                    const queryId = this.dataset.query
                    const filterKey = this.dataset.filter

                    // Update selected values
                    selectedValues[queryId][filterKey] = this.value

                    const sparqlQuery = queryResolver(queryId, {
                        modality: selectedValues[queryId].modality,
                        task: selectedValues[queryId].task,
                        type: selectedValues[queryId]["resource-type"]
                    })
                    
                    const venusChart = document.querySelector(`#${queryId}-venus`);
                    venusChart.sparqlResults = null
                    venusChart.sparqlQuery = sparqlQuery
                    await venusChart.launch();

                })
        }
        
    }
}

