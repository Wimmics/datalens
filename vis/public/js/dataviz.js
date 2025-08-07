class DataViz{
    constructor() {
        this.component = null

        this.intervalId = null
    }

    async init() {
        this.config = await this.fetchConfig()
        console.log("DataViz config:", this.config)
    }

    async reset() {
        if (this.component)
            this.component.remove()

        this.component = document.createElement("mge-dashboard")
        this.component.setAttribute("id", "visualization-content")

        document.querySelector(".dashboard").appendChild(this.component)

        this.component.disableView('mge-annotation')
        this.component.disableView('mge-glyph-matrix')
        this.component.disableView('mge-query')
        this.component.disableInitialQueryPanel()
    }

    setLoadingMessage(message) {
        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `Elapsed time: ${mins}m ${secs.toString().padStart(2, '0')}s`;
        }

        let startTime = Date.now()

        this.togglePlaceholder(`${this.getLoadingHTML()}${message}`)
        // Start interval to update time every second
        this.intervalId = setInterval(() => {
            const seconds = Math.floor((Date.now() - startTime) / 1000);
            this.togglePlaceholder(`${this.getLoadingHTML()}${message} <br><strong>${formatTime(seconds)}</strong>`)
        }, 1000);
    }

    getLoadingHTML() {
        
        return `<div class="loading-spinner"></div>`
    }

    async set(filters) {
        await this.reset()
        
        this.setLoadingMessage('Fetching and processing data. Please bear with us as this may take some time.')
        // this.togglePlaceholder(`${this.getLoadingHTML()}<br>Fetching and processing data. Please bear with us as this may take some time.`)
        
        let query = await this.getQuery(filters)
        if (!query) return

        let result = await this.runQuery(query)
        if (!result) return

        console.log("Query result:", result)
        
        
        clearInterval(this.intervalId);
        if (!result.length) {    
            this.togglePlaceholder("The current filters do not match any data.")
        } else { 
            // if (!result.date)
            //     this.component.disableView('mge-barchart')
            // else this.component.enableView('mge-barchart')
            this.togglePlaceholder(null)
            // this.component.resetDashboard()
            
            // this.component.innerHTML = null

            this.display({ data: result, stylesheet: null })
            
            // this.updateVisualizationTitle(result.stylesheet.appli.name)
        }
    }

    async getQuery(filters) {

        if (!this.config) {
            clearInterval(this.intervalId);
            this.togglePlaceholder(`<i class="fa-solid fa-triangle-exclamation alert-icon"></i><br>Link type "${filters.link}" is not supported.`)
            return
        }

        let equalNodes = filters.source === filters.target
        let queryFile = equalNodes ? this.config['author-query'] : this.config['spo-query']

        let queryTemplate = await fetch(`/datalens/sparql-mge/config/${queryFile}`);
        if (!queryTemplate.ok) {
            clearInterval(this.intervalId);
            this.togglePlaceholder(`<i class="fa-solid fa-triangle-exclamation alert-icon"></i><br>Error fetching query: ${queryTemplate.statusText}`)
            return
        }

        let query = await queryTemplate.text();
        
        let sourcePattern, targetPattern, filterExists;
        if (equalNodes) {
            let pattern = this.config?.attrs[filters.source]
            if (!pattern) {
                this.togglePlaceholder(`<i class="fa-solid fa-triangle-exclamation alert-icon"></i><br>Source/Target "${filters.source}" is not supported.`)
                return
            }
            // If source and target are the same, we use the same pattern for both
            sourcePattern = pattern.replace(/\?\$key/g, `?n`);

            if (Object.keys(filters).includes(filters.source) && filters[filters.source].length > 0) {
                let valuesStr = filters[filters.source].map(value => `"${value}"`).join(', ')
                filterExists = `FILTER EXISTS {
                    ${pattern.replace(/\?\$key/g, `?match`)} 
                    FILTER(?match IN ( ${valuesStr} ))
                }`
            }
            
        } else {
            sourcePattern = this.config?.attrs[filters.source]
            targetPattern = this.config?.attrs[filters.target]

            if (!sourcePattern || !targetPattern) {
                this.togglePlaceholder(`<i class="fa-solid fa-triangle-exclamation alert-icon"></i><br>Source/Target "${filters.source}" or "${filters.target}" is not supported.`)     
                return
            }

            sourcePattern = sourcePattern.replace(/\?\$key/g, `?${filters.source}`);
            targetPattern = targetPattern.replace(/\?\$key/g, `?${filters.target}`);
        }

        let themePattern = null;
        if (filters.source !== filters.theme && filters.target !== filters.theme) {
            themePattern = this.config?.attrs[filters.theme]
            if (themePattern) {
                themePattern = themePattern.replace(/\?\$key/g, `?${filters.theme}`);
            }
        }

        let linkPattern = this.config?.links[filters.link]
        if (linkPattern) {
            linkPattern = linkPattern.replace(/\?\$key/g, `?${filters.link}`);
        }

        let datasetPattern = filters.link === 'dataset' ? this.config?.dataset : null;
    
        let filtersPatterns = []
        let valuesPatterns = []

        let nodeKeys = [filters.source, filters.target, filters.theme, filters.link]
        let keys = Object.keys(filters).filter(key => !['source', 'target', 'theme', 'link'].includes(key))

        for (let key of keys) {
            if (filters[key].length === 0) 
                continue // Skip empty filters
            
            // If the key is one of the node keys, we only add a FILTER pattern
            let values = filters[key].map(value => `"${value}"`)
            if (nodeKeys.includes(key)) { // If the key is a node key, we can use VALUES clause
                if (equalNodes && key === filters.source) 
                    continue // Skip if source and target are the same 

                valuesPatterns.push(`VALUES ?${key} { ${values.join(' ')} } .`)
            } 
            else if (['issued', 'modified'].includes(key)) { // If the key is a date, we use FILTER
                let pattern = this.config?.attrs[key]
                if (!pattern) continue // Skip if no pattern is defined for the key

                if (filters.link === 'dataset' && key !== 'issued') {
                    filtersPatterns.push(pattern.replace(/\?\$key/g, `?${key}`))
                } 

                if (filters[key].length === 1) { // If the date is a single value, we can use YEAR function    
                    filtersPatterns.push(`FILTER (YEAR(?${key}) = ${filters[key]}) .`)
                } else {
                    filtersPatterns.push(`FILTER( STR(YEAR(?${key})) IN ( ${values.join(', ')} ) ) .`)
                }
            }
            else if (['downloadCount', 'likesCount'].includes(key)) {
                let pattern = this.config?.attrs[key]
                if (!pattern) continue // Skip if no pattern is defined for the key

                filtersPatterns.push(pattern.replace(/\?\$key/g, `?${key}`))
               
                let vals = filters[key][0].replace(/[–—]/g, '-').split('-').map(v => Number(v.trim())) 
                let [min, max] = d3.extent(vals)

                filtersPatterns.push(`FILTER( ?${key} > ${min} && ?${key} <= ${max} ) .`)
            }
            else { // Otherwise, we need to bind the values and filter them
                let pattern = this.config?.attrs[key]
                if (!pattern) continue // Skip if no pattern is defined for the key

                filtersPatterns.push(pattern.replace(/\?\$key/g, `?${key}`))
                filtersPatterns.push(`FILTER( STR(?${key}) IN ( ${values.join(', ')} ) ) .`)
            }
            
        }
        console.log("Filters patterns:", filtersPatterns)

        let bindingsPatterns = []
        Object.keys(this.config.bindings).forEach(key => {
            if (equalNodes && (key === 'target' || key === 'source')) return // Skip if source and target are the same

            if (filters[key] && this.config.bindings[key]) {
                let pattern = this.config.bindings[key].replace(/\?\$key/g, `?${filters[key]}`);
                bindingsPatterns.push(pattern);
            }
        })

        if (!filters.theme) 
            bindingsPatterns.push(`BIND ("Not Provided" as ?type) .`)

        if (filters.link != 'dataset') 
            bindingsPatterns.push(`BIND ("Not Provided" as ?date) .`)
        else {
            bindingsPatterns.push(`BIND (?issued as ?date) .`)
        }
        

        // Replace placeholders in the query template
        function replacePatternPlaceholders(query, values) {
            for (const [key, value] of Object.entries(values)) {
                const pattern = new RegExp(`#\\s*\\$${key}\\b`, 'g');
                query = query.replace(pattern, value);
            }
            return query;
        }

        const values = {
            datasetPattern: datasetPattern || '',
            valuesPattern: valuesPatterns.join('\n'),
            themePattern: themePattern || '',
            linkPattern: linkPattern || '',
            bindingPattern: bindingsPatterns.join('\n'),
            filtersPattern: filtersPatterns.join('\n'),

            // Source and target patterns
            sourcePattern: !equalNodes ? (sourcePattern || '') : '',
            targetPattern: targetPattern || '',

            // If source and target are the same, we use the same pattern for both
            nodesPattern: equalNodes ? (sourcePattern || '')  : '',
            filterExists: filterExists || '',
        }

        query = replacePatternPlaceholders(query, values);

        console.log("Final query:", query)

        return query
    }

    async runQuery(query) {
        let body = {
            query: query,
            batch: true // Set to true if you want to run the query in batch mode
        }
        try {
            const result = await fetch('/datalens/sparql-mge/query-endpoint', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            }).then(res => res.json())
            
            if (result.error) {
                clearInterval(this.intervalId);
                this.togglePlaceholder(`Error running the query: ${result.error}. <br>Please try again later.`)
                return null;
            }
            return result?.bindings || result; // Return the bindings or the result directly if no bindings are present

        } catch (error) {
            clearInterval(this.intervalId);
            this.togglePlaceholder(`Error running the query: ${error}. <br>Please try again later.`)
            console.error('Error running query:', error);
            return null;
        }
    }
    

    display(result) {
        // change the data in the visualization and display it
        this.component.setData(result.data, result.stylesheet)
        
        this.component.setDashboard()
    }

    updateVisualizationTitle(title) {
        document.querySelector("#viz-title").textContent = `Visualization: ${title}`
    }

    togglePlaceholder(message) {
        const placeholder = document.getElementById('placeholder');
        const visualizationContent = document.getElementById('visualization-content');
    
        if (!message) {
            placeholder.style.display = 'none';
            visualizationContent.style.display = 'block';
        } else {
            placeholder.style.display = 'block';
            visualizationContent.style.display = 'none';
            placeholder.innerHTML = message
        }
    }

    // Configuration fetching function
    // Contains the basic data structure for filters
    async fetchConfig() {
        try {
            const response = await fetch('/datalens/sparql-mge/config.json');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching config data:', error);
        }
    }

    // async fetchData(filters) {
   
    //     try {
    //         const response = await fetch('/datalens/data/datavis', {
    //             method: 'POST',
    //             headers: {
    //                 'Content-Type': 'application/json'
    //             },
    //             body: JSON.stringify(filters)
    //         });
    
    //         if (!response.ok) {
    //             console.error('There was a problem.');
    //             return;
    //         }
    
    //         return await response.json()
    
    //     } catch (error) {
    //         this.togglePlaceholder(`Error fetching the data: ${error}. <br>Please try again later.`)
    //         //console.error('Error fetching data:', error);
    //     }
    
    //     return
    
    //   }
}