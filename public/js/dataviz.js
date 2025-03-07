class DataViz{
    constructor() {
        this.component = null
    }

    async init() {
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

    getLoadingHTML() {
        return `<div class="loading-spinner"></div>`
    }

    async set(filters) {
        
        this.togglePlaceholder(`${this.getLoadingHTML()}<br>Fetching and processing data. Please bear with us as this may take some time.`)
        let result = await this.fetchData(filters)
        
        console.log(result)
        if (result.message) {
            this.togglePlaceholder(`<i class="fa-solid fa-triangle-exclamation alert-icon" ></i><br> ${result.message}`)
        } else if (!result.data.length) {
            this.togglePlaceholder("The current filters do not match any data.")
        } else { 
            if (!result.data[0].date)
                this.component.disableView('mge-barchart')
            else this.component.enableView('mge-barchart')

            //this.component.resetDashboard()
            this.component.innerHTML = null
            this.togglePlaceholder(null)

            this.display(result)
            this.updateVisualizationTitle(result.stylesheet.appli.name)
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

    async fetchData(filters) {
   
        try {
            const response = await fetch('/datalens/data/datavis', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(filters)
            });
    
            if (!response.ok) {
                console.error('There was a problem.');
                return;
            }
    
            return await response.json()
    
        } catch (error) {
            this.togglePlaceholder(`Error fetching the data: ${error}. <br>Please try again later.`)
            //console.error('Error fetching data:', error);
        }
    
        return
    
      }
}