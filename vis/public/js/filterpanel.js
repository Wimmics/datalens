class FilterPanel {
    constructor(savedFilters) {
        this.data // all posible filters

        this.filters = savedFilters ? JSON.parse(savedFilters) : {}

        this.checkboxFilters = ["issued", "modified", "downloadCount", "likesCount", "size"]
        this.networkDimensions = ['source', 'target', 'theme', 'link']
    }

    async set() {
        
        this.data = await this.fetchConfig()

        if (!this.data) {
            console.error('Failed to fetch config data');
            return;
        }
        await this.fetchData()

        await this.generateFilters()

        await this.restoreFilters()

        await this.setNetworkOptions()

    }

    getSelectedFilters() {
        return this.filters
    }

    // Function to capitalize the first letter and remove underscores or hyphens from a string
    prettyTitle(key) {
        // Replace underscores or hyphens with spaces, capitalize first letter, and then capitalize the rest
        return key
            .replace(/[_-]/g, ' ') // Replace underscores or hyphens with spaces
            .replace(/\b\w/g, char => char.toUpperCase()); // Capitalize the first letter of each word
    }

    saveFilters(key, value) {   
       
        if (this.filters[key]) {
            if (Array.isArray(value)) {
                if (!this.filters[key].length) {
                    this.filters[key] = value
                } else if (this.filters[key].every(d => value.includes(d)))
                    this.filters[key] = []
                else this.filters[key] = value
            }
            else if (this.filters[key].includes(value)) {
                this.filters[key] = this.filters[key].filter(d => d !== value)
            } else {
                this.filters[key].push(value)
            }
        } else {
            if (Array.isArray(value))
                this.filters[key] = value
            else this.filters[key] = [ value ]
        }

        window.sessionStorage.setItem('filters', JSON.stringify(this.filters))
    }

    async restoreFilters() {
        let savedFilters = window.sessionStorage.getItem('filters') 
        
        if (!savedFilters) return
        this.filters = JSON.parse(savedFilters)

        // update the selections according to filters in the sessionStorage
        for (let key of Object.keys(this.filters)) {
            if (this.networkDimensions.includes(key)) continue // Skip network dimensions
            
            const values = this.filters[key]

            if (this.checkboxFilters.includes(key)) {
                for (let value of values) {
                    const checkbox = document.querySelector(`input[name="${key}"][value="${value}"]`);
                    if (checkbox) {
                        checkbox.checked = true; // Check the saved checkboxes
                    }
                }
            } else {
                for (let value of values) {
                    this.renderSelectedValue(key, value)
                }
            }
        }
    }
    

    // Function to create input with datalist for strings, allowing multiple selection
    createDataListInput(key, values) {
        const options = values.map(item => `<option value="${item.value}">${item.value} (${item.count})</option>`).join('');
        const prettyKey = this.prettyTitle(key);

        return `
            <div class="mb-3">
                <label for="${key}" class="form-label">${prettyKey}</label>
                <input type="text" class="form-control multi-select-input" id="${key}-input" placeholder="Choose ${prettyKey}..." list="${key}-datalist">
                <datalist id="${key}-datalist">
                    ${options}
                </datalist>
                <div id="${key}-selected" class="selected-items mt-2"></div>
            </div>
        `;
    }

   // Function to initialize multi-select functionality for all inputs at once
    initAllMultiSelectInputs() {
        const multiSelectInputs = document.querySelectorAll('.multi-select-input');
        
        multiSelectInputs.forEach(inputElement => {
            const key = inputElement.id.replace('-input', '');  // Extract the key from the input ID
            this.initMultiSelectInput(key);  // Initialize multi-select for each input
        });
    }

    // Function to render the selected values
    renderSelectedValue(key, value) {
        const _this = this;

        const selectedContainer = document.querySelector(`#${key}-selected`);

        const span = document.createElement('span');
        span.setAttribute('class', "badge bg-light text-dark mr-2");
        span.style.marginLeft = '10px'
        span.textContent = value

        const button = document.createElement('button');
        button.setAttribute('class', "btn btn-sm btn-danger remove-btn");
        button.setAttribute('type', 'button');
        button.style.marginLeft = '5px'
        button.innerHTML = '&times;';  

        button.addEventListener('click', function() {
            _this.saveFilters(key, value);  // Save filters with the current key and value
            this.parentNode.remove();  // Remove the badge
        });

        span.appendChild(button);
        selectedContainer.appendChild(span);

    }

    // Function to initialize multi-select functionality for a single input
    initMultiSelectInput(key) {
        const inputElement = document.querySelector(`#${key}-input`);


        // Add event listener to input field to capture selection
        inputElement.addEventListener('input', (event) => {
            
            const value = event.target.value.trim();
            let validValues = this.data.find(d => d.key === key)?.values.map(d => d.value) || [];
        
            if (value && validValues.includes(value)) {
                if (this.filters[key] && this.filters[key].includes(value)) return

                this.renderSelectedValue(key, value);  // Render the updated list
                this.saveFilters(key, value)

                inputElement.value = '';  // Clear the input after adding the selection
            }
            console.log(this.filters)
            
        });

        // Handle Enter key or value selection from the datalist
        inputElement.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && inputElement.value.trim()) {
                const value = inputElement.value.trim();
                
                if (this.filters[key] && this.filters[key].includes(value)) return
                
                this.renderSelectedValue(key, value);  // Render the updated list
                this.saveFilters(key, value)

                inputElement.value = '';  // Clear the input after selection
            }
        });
    }


    // Function to convert range string to comparable numeric values
    convertToNumber(str) {
        const value = str.match(/\d+\.?\d*/g);  // Extract the number part
        const unit = str.match(/[KMGTB]/);      // Extract the unit (K, M, B, T)
        
        let num = parseFloat(value[0]);         // Get the first number in the range
        
        if (unit) {
            switch (unit[0]) {
                case 'K': return num * 1e3;     // Thousand
                case 'M': return num * 1e6;     // Million
                case 'B': return num * 1e9;     // Billion
                case 'T': return num * 1e12;    // Trillion
            }
        }
        
        return num;  // Return plain number if no unit found (e.g., "n<1K")
    }

    safeString(str) {
        return str.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Function to create a radio list for 'size_categories'
    createCheckboxList(key, values) {
        const prettyKey = this.prettyTitle(key);
        
        const checkboxButtons = values.map(item =>
            `
                <div class="form-check">
                    <input class="form-check-input filter-checkboxes" type="checkbox" name="${key}" id="${key}-${this.safeString(item.value)}" value="${this.safeString(item.value)}">
                    <label class="form-check-label " for="${key}-${this.safeString(item.value)}">
                        ${this.safeString(item.value)} <span style='margin-left: 5px; font-size: 10px;'>(${item.count})</span>
                    </label>
                </div>
            `
        ).join('');

        return `
            <div class="mb-3">
                <label class="form-label">${prettyKey}</label>
                ${checkboxButtons}
            </div>
        `;
    }

    setInteractors() {
        
        const _this = this;

        this.initAllMultiSelectInputs()

        let checkboxes = document.querySelectorAll('.filter-checkboxes')
        for (let cb of checkboxes) {
            cb.addEventListener('change', function () {
                let value = this.value
                if (['downloads', 'likes'].includes(this.name)) {
                    value = value.split('-').map(d => +d)                    
                }
               
                _this.saveFilters(this.name, value)        
            })
        }

    }

    createJenksBreaks(values, numClasses) {
        const breaks = ss.jenks(values, numClasses);

        // Check if the last break has the same lower and upper bound
        const lastIndex = breaks.length - 1;
        if (breaks[lastIndex] === breaks[lastIndex - 1]) {
            // Remove the last duplicate break
            breaks.splice(lastIndex - 1, 1);
        }

        const results = [];

        for (let i = 0; i < breaks.length - 1; i++) {
            const lower = breaks[i];
            const upper = breaks[i + 1];

            const count = values.filter(v =>
                (i === breaks.length - 2)
                ? v >= lower && v <= upper   // include upper in last bin
                : v >= lower && v < upper    // exclude upper in others
            ).length;

            results.push({
                value: `${lower}–${upper}`,
                count: count
            });
        }
        return results;
    }   

    // Function to generate filters dynamically based on data
    async generateFilters() {
        const filtersContainer = document.querySelector('#filters-container');

        for (let item of this.data) {
            if (['downloadCount', 'likesCount'].includes(item.key)) {
                let values = this.createJenksBreaks(item.values.map(d => d.count), 7);
                filtersContainer.innerHTML += this.createCheckboxList(item.key, values);
            }
            else if (this.checkboxFilters.includes(item.key) ) {
                let values = item.values.sort((a, b) => this.convertToNumber(a.value) - this.convertToNumber(b.value));
                filtersContainer.innerHTML += this.createCheckboxList(item.key, values);
            } 
            else {
                let values = item.values.sort((a, b) => b.count - a.count);
                filtersContainer.innerHTML += this.createDataListInput(item.key, values);
            }
        }

        this.setInteractors()
    }

    async setNetworkOptions() {
        let variables = ['dataset', 'taskCategory', 'task', 'modality', 'license', 'format', 'language']

        this.setSelect(variables, '#source-select', this.filters.source || 'taskCategory')
        this.setSelect(variables, '#target-select', this.filters.target || 'taskCategory')
        this.setSelect(variables, '#link-select', this.filters.link ||'dataset')

        let themeVariables = ['modality', 'license', 'format', 'size', 'language']
        this.setSelect(themeVariables, '#theme-select', this.filters.theme || 'license')
    } 

    async setSelect(data, selector, selectedValue) {
        d3.select(selector)
            .selectAll('option')
            .data(data)
            .join(
                enter => enter.append('option'),
                update => update,
                exit => exit.remove()
            )
            .attr('value', d => d)
            .text(d => this.prettyTitle(d))
            .property('selected', d => d === selectedValue)
    }

    // Configuration fetching function
    // Contains the basic data structure for filters
    async fetchConfig() {
        try {
            const response = await fetch('/datalens/sparql-filters/config.json');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching config data:', error);
        }
    }

    // Function to fetch data for each filter using a SPARQL query
    async fetchData() {

        for (let filter of this.data) {
            
            if (!filter.query) {
                console.warn(`No query defined for filter: ${filter.label}`);
                return;
            }

            let data = await fetch(`/datalens/sparql-filters/query-endpoint/${filter.query}`)
                .then(res => res.json())
            
            if (data.error) {
                console.error(`Error fetching data for filter: ${filter.label}`, data.error);
                continue;
            }
            
            if (!data || !data?.results?.bindings?.length) {
                console.warn(`No data found for filter: ${filter.label}`);
                continue;
            }
            
            filter.values = data.results.bindings
                .map(d => ({ value: d.value.value, count: +d.count.value}))
        }

        console.log('All filters data fetched successfully:', this.data);

        
    }
}