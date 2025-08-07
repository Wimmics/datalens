/*
    * DataTools class for processing and visualizing dataset relationships.
    * It uses data from HuggingFace, extracted directly from the API.
    * This class handles loading dataset files, filtering data based on user-defined criteria,
    * and generating network visualizations.
    * It also provides methods for extracting tag values, formatting dates, and creating datasets as nodes
    * or links in a network.
    * @author Aline Menin
    * @version 1.0
    * @license Apache 2.0
    */
'use strict';


const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

const simpleStatistics = require('simple-statistics');

class DataTools {
    constructor(folderPath) {
        this.folderPath = folderPath;
        this.data;

        this.invalidKeys = ['description', 'citation', 'sha', 'private', 'disabled', 'downloads_all_time', 'id',  'paperswithcode_id', 'region', 'card_data', 'siblings', 'cardData', '_id', 'key', 'arxiv', 'doi', 'icelandic',  'Norwegian wikipedia scraped with links from nowiki dump', 'author', 'lastModified', 'gated', 'library', 'annotations_creators', 'language_creators', 'source_datasets', 'benchmark', 'multilinguality', 'ai-tube']
    }

    async init(action, filters) {
        this.action = action
        this.filters = {... filters}

        await this.loadData()
      
        if (this.filters && Array.isArray(this.data)) {
            // console.log(`Resulting dataset: ${this.data.length} records.`)
            
        } else {
            // Calculate Jenks natural breaks for downloads and likes
            if (this.downloadValues.length > 0) {
                const downloadBreaks = simpleStatistics.jenks(this.downloadValues, 10); 
                this.data.downloads = this.countItemsInBreaks(this.downloadValues, downloadBreaks);
            }

            if (this.likeValues.length > 0) {
                const likeBreaks = simpleStatistics.jenks(this.likeValues, 10); 
                this.data.likes = this.countItemsInBreaks(this.likeValues, likeBreaks);
            }

            await fs.writeFile(path.join(__dirname, 'data/filters.json'), JSON.stringify(this.data, null, 4))
        }
    }

    // Helper function to count items in each Jenks break
    countItemsInBreaks(values, breaks) {
        const counts = {};

        for (let i = 1; i < breaks.length; i++) {
            const rangeKey = `${breaks[i - 1]} - ${breaks[i]}`;
            counts[rangeKey] = values.filter(v => v >= breaks[i - 1] && v <= breaks[i]).length;
        }

        return counts;
    }

    /**
     * Ensures that a folder exists, creating it if necessary.
     * @param {string} cachePath - The relative path of the folder to check/create.
     */
    async ensureFolderExists(cachePath) {
        const fullPath = path.join(__dirname, cachePath);

        try {
            // Check if folder exists
            await fs.access(fullPath); // No error means the folder exists
        } catch (error) {
            // If access fails, create the folder
            await fs.mkdir(fullPath, { recursive: true });
        }
    }

    /**
     * Creates a hash from the filters object.
     * @param {Object} filters - The filters object to hash.
     * @returns {string} - The resulting hash as a hexadecimal string.
     */
    getFilterHash(filters) {
        // Convert the filters object to a JSON string
        const filtersString = JSON.stringify(filters);

        // Create a hash from the JSON string
        const hash = crypto.createHash('sha256'); // You can choose a different algorithm if needed
        hash.update(filtersString);
        return hash.digest('hex'); // Returns the hash as a hexadecimal string
    }

    async getData() {
        if (this.action === 'datavis') {
            let cachePath = '/data/cache'
            await this.ensureFolderExists(cachePath)

            let data;
            
            if (this.filters.source === 'dataset' && this.filters.source === this.filters.target)
                data = await this.createDatasetNetwork()
            else if (this.filters.link === 'dataset')
                data = await this.datasetAsLink()
            else if (this.filters.source === 'dataset' || this.filters.target === 'dataset')
                data = await this.datasetAsNode()

            let filename = `data/cache/${this.getFilterHash(this.filters)}.json`
            try {
                await fs.writeFile(path.join(__dirname, filename), JSON.stringify(data, null, 4))
            } catch (e) {
                console.log(`Error while writing the file ${filename}: ${e}`)
            }
            return data
        }            

        return this.data
    }




    // Function to load all JSON files from a folder
    async loadData() {
        try {
            // Read directory asynchronously
            const files = await fs.readdir(this.folderPath);
    
            // Process each file asynchronously
            for (const file of files) {
                if (file.endsWith('.json')) {
                    const filePath = path.join(this.folderPath, file);
                    // console.log(`Processing file: ${filePath}`);
    
                    // Read file content asynchronously
                    const data = JSON.parse(await fs.readFile(filePath, 'utf8'));
                    // console.log(`Total entries in ${file}: ${data.length}`);
    
                    // Process data in chunks to avoid memory issues
                    const chunkSize = 1000; // Adjust chunk size as needed
                    for (let i = 0; i < data.length; i += chunkSize) {
                        const chunk = data.slice(i, i + chunkSize);
                        // console.log(`Chunk ${i/chunkSize} of ${Math.trunc(data.length/chunkSize)}`)
                        switch (this.action) {
                            case 'datavis':
                                await this.getFilteredData(chunk);
                                break;
                            case 'filters':
                                await this.getFilterOptions(chunk);
                                break;
                        }
    
                        // Optionally, process each chunk here if needed
                    }
                }
            }
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    // Function to format date strings (YYYY-MM) into a numeric format (YYYYMM)
    formatDateToNumeric(dateString) {
        // Ensure the input follows the 'YYYY-MM' format
        const [year, month] = dateString.split('-');
        return parseInt(`${year}${month}`, 10);  // Combine year and month as a number (e.g., 202303 for March 2023)
    }

    isDate(str) {
        const datePattern = /^\d{4}-(0[1-9]|1[0-2])$/;
        return datePattern.test(str);
    }

    async getFilteredData(chunk) {

        const matches = async (item) => {
            // Extract tag values
            const tags = await this.extractAllTagValues(item.tags);

            const filterKeys = Object.keys(this.filters)

            let match = filterKeys.map(key => {
                const filterValues = this.filters[key];
                // Get item value based on key
                const itemValue = item[key];
            
                
                // If filter is empty, the condition is met
                if (!Array.isArray(filterValues) || filterValues.length === 0) return true;
                
                // If the key exists in the item, check the value against the filter
                if (itemValue) {
                    
                    // Handle numeric ranges for specific keys
                    if (filterValues.length === 2) {
                        const [min, max] = filterValues;
                        
                        if (typeof min === 'number' && typeof max === 'number') {
                            return itemValue >= min && itemValue <= max;
                        } 
                    } else if (['created_at', 'last_modified'].includes(key)) {
                        return filterValues.includes(this.formatDateToYear(itemValue).toString())
                    }
                    // For other types of filters (non-range), check if the itemValue is included in the filter array
                    return filterValues.includes(itemValue);
                }
                
                // If the key does not exist in the item, check against tags
                if (key in tags) {
                    return filterValues.some(filter => tags[key].includes(filter));
                }
                
                // Check if the filter values exist in the tags
                return filterValues.some(filter => Object.values(tags).flat().includes(filter));
            });

            return match.every(d => d) // TODO: do be defined interactively
        }

        // Use Promise.all to handle the async filter function
        const results = await Promise.all(chunk.map(async (item) => {
            // Check if the item matches the filters
            return await matches(item);
        }));

        // Filter the data based on the results
        
        if (!this.data) this.data = []
        this.data = this.data.concat(chunk.filter((_, index) => results[index]))
    }
    
    // Updated extractTagValues to handle multiple keys dynamically
    async extractAllTagValues(tags) {
        const values = {};
        if (Array.isArray(tags)) {
            tags.forEach(tag => {
                const [tagKey, tagValue] = tag.split(':', 2);
                if (this.invalidKeys.includes(tagKey)) return

                if (tagKey && tagValue) {
                    if (!values[tagKey]) {
                        values[tagKey] = [];
                    }
                    if (!values[tagKey].includes(tagValue)) {
                        values[tagKey].push(tagValue);
                    }
                }
            });
        }
        return values;
    }
    

    isDateString(dateStr) {
        // Check if the string follows the pattern 'YYYY-MM-DD'
        return /^\d{4}-\d{2}-\d{2}/.test(dateStr);
    }
    

    // Helper function to extract only the year and month from the date
    formatDateToYearMonth(dateStr) {
        // Extract year and month from the date
        const date = new Date(dateStr);
        const year = date.getUTCFullYear();
        const month = (date.getUTCMonth() + 1).toString().padStart(2, '0'); // Months are zero-indexed
        return `${year}-${month}`;
    }

     // Helper function to extract only the year and month from the date
     formatDateToYear(dateStr) {
        // Extract year and month from the date
        const date = new Date(dateStr);
        return date.getUTCFullYear();
        
    }


    async getFilterOptions(chunk) {
        if (!this.data) this.data = {
            modality: {},
            task_categories: {},
            task_ids: {},
            license: {},
            size_categories: {},
            format: {},
            language: {},
            created_at: {},
            last_modified: {},
            downloads: {},
            likes: {},
        }

        this.downloadValues = [];
        this.likeValues = [];

        for (let item of chunk) {
            for (let key of Object.keys(item)) {
                if (this.invalidKeys.includes(key)) continue;

                if (key === 'tags' && Array.isArray(item[key])) {
                    for (let tag of item[key]) {
                        const [tagKey, tagValue] = tag.split(':', 2);

                        if (this.invalidKeys.includes(tagKey)) continue;

                        if (tagKey && tagValue) {
                            if (!this.data[tagKey]) {
                                this.data[tagKey] = {};
                            }
                            if (!(tagValue in this.data[tagKey])) {
                                this.data[tagKey][tagValue] = 0;
                            } else this.data[tagKey][tagValue]++;
                        }
                    }
                } else if (item[key] !== null && item[key] !== undefined) {
                    if (!this.data[key]) continue;

                    if (this.isDateString(item[key])) {
                        const year = this.formatDateToYear(item[key]);

                        if (!(year in this.data[key])) {
                            this.data[key][year] = 0;
                        } else this.data[key][year]++;
                    } else {
                        // Collect download and like values for Jenks breaks calculation
                        if (key === 'downloads') {
                            this.downloadValues.push(+item[key]);
                        } else if (key === 'likes') {
                            this.likeValues.push(+item[key]);
                        } else {
                            if (!(item[key] in this.data[key])) {
                                this.data[key][item[key]] = 0;
                            } else this.data[key][item[key]]++;
                        }
                    }
                }
            }
        }

        
    }

    


    // Function to combine values from two data objects
    async combinedValues(dt1, dt2, key) {
        const valuesDt1 = this.extractValues(dt1, key);
        const valuesDt2 = this.extractValues(dt2, key);
        return {
            [dt1.id]: valuesDt1,
            [dt2.id]: valuesDt2
        };
    }

    // Helper function to extract tag values based on the provided key
    extractTagValues(tags, key) {
        return tags
            .filter(tag => tag.startsWith(`${key}:`))
            .map(tag => tag.split(`${key}:`)[1]);
    }

    // Function to capitalize the first letter and remove underscores or hyphens from a string
    prettyTitle(key) {
        // Replace underscores or hyphens with spaces, capitalize first letter, and then capitalize the rest
        return key
            .replace(/[_-]/g, ' ') // Replace underscores or hyphens with spaces
            .replace(/\b\w/g, char => char.toUpperCase()); // Capitalize the first letter of each word
    }

    async datasetAsNode() {
        const network = []

        let currentItemNumber = 1;
        const totalDatasets = this.data.length;

        try {
            for (let item of this.data) { // iterate over datasets (links)
                // console.log(`Processing dataset ${item.id} (${currentItemNumber}/${totalDatasets}).`);

                let targets = this.extractTagValues(item.tags, this.filters.source === 'dataset' ? this.filters.target : this.filters.source) // extract values for target
                let links = this.extractTagValues(item.tags, this.filters.link)

                let type = this.extractTagValues(item.tags, this.filters.theme)[0] // extract values for theme (?type)
                if (type && type === 'unknown')
                    type = null

                for (let link of links) {
                    for (let target of targets) {
                        const value = {
                            p: { value: link },
                            s: { value: item.id },
                            o: { value: target },
                            label: { value: link },
                            style1: { value: 'fst' },
                            style2: { value: 'snd' }    
                        }     

                        network.push(value)
                    }
                }

            }   

            let stylesheet = this.getStylesheet()
            delete stylesheet['services']

            stylesheet.appli.name = `Relationship between ${this.prettyTitle(this.filters.source)} and ${this.prettyTitle(this.filters.target)} based on shared ${this.prettyTitle(this.filters.link)}`   

            return {
                data: network,
                stylesheet: stylesheet
            }
        } catch(e) {
            return { message: `Data processing failed with error: ${e.message}`}
        }

    }

    // Function to create a dictionary of tasks from the data
    async datasetAsLink() {

        const network = []

        let currentItemNumber = 1;
        const totalDatasets = this.data.length;
        try {
            for (let item of this.data) { // iterate over datasets (links)
                // console.log(`Processing dataset ${item.id} (${currentItemNumber}/${totalDatasets}).`);

                let sources = this.extractTagValues(item.tags, this.filters.source) // extract values for source 
                let targets = this.extractTagValues(item.tags, this.filters.target) // extract values for target

                let type = this.extractTagValues(item.tags, this.filters.theme)[0] // extract values for theme (?type)
                if (type && type === 'unknown')
                    type = null

                let size = this.extractTagValues(item.tags, 'size_categories')[0] // only for completing the label

                for (let i = 0; i < sources.length; i++) {
                    for (let j = 0; j < targets.length; j++) {
                        
                        const value = {
                            p: { value: item.id },
                            s: { value: sources[i] },
                            o: { value: targets[j] },
                            url: { value: `https://huggingface.co/datasets/${item.id}`},
                            label: { value: `${item.id} ${size ? '(' + size + ')' : ''}`},
                            date: { value: item.last_modified },
                            authorList: { value: `Author: ${item.author}. Description: ${item.description}` },
                            type: { value: type }
                        }

                        if (this.filters.source !== this.filters.target) {
                            value.style1 = { value: 'fst' }
                            value.style2 = { value: 'snd' }
                        }

                        network.push(value)
                        
                    }
                }

                currentItemNumber++;
            }

            let stylesheet = this.getStylesheet()
            delete stylesheet['services']
            if (this.filters.source === this.filters.target)
                stylesheet.appli.name = `Relationship between ${this.prettyTitle(this.filters.source)} based on shared datasets`
            else  stylesheet.appli.name = `Relationship between ${this.prettyTitle(this.filters.source)} and ${this.prettyTitle(this.filters.target)} based on shared datasets`   

            return {
                data: network,
                stylesheet: stylesheet
            }
        } catch(e) {
            return { message: `Data processing failed with error: ${e.message}`}
        }
        
    }

    // Function to create dataset network
    async createDatasetNetwork() { // both source and target are datasets

          // Function to create a dictionary of tasks from the data
        const extractDict = async (key) => {
            let dict = {}

            this.data.forEach(item => {
                const tasks = this.extractTagValues(item.tags, key)
                tasks.forEach(task => {
                    if (dict[task]) {
                        dict[task].push(item._id)
                    } else {
                        dict[task] = [item._id];
                    }
                });
            });

            return dict
        }
      
        let itemsDict = await extractDict(this.filters.link)

        const totalTasks = Object.keys(itemsDict).length;
        let currentTaskNumber = 1;

        const network = []

        try {
            for (const key of Object.keys(itemsDict)) { 
                const itemList = itemsDict[key]
                const arraySize = itemList.length;
                // console.log(`Processing task ${key} (${currentTaskNumber}/${totalTasks}). Array size: ${arraySize}`);

                let authors = itemList.map(d => {
                    let dt = this.data.find(e => e._id === d); 
                    return dt ? dt.id : null
                })

                authors = authors.filter(d => d)

                const value = {
                    p: { value: key },
                    author: { value: authors.join('--') },
                    label: { value: key },
                    url: this.filters.link === 'model' ? { value: `https://huggingface.co/${key}`} : null,
                };
                network.push(value);


                currentTaskNumber++;

            }

            let stylesheet = this.getStylesheet()
            stylesheet.appli.name = `The relationship between datasets based on shared ${this.prettyTitle(this.filters.link)}`
            return {
                data: network,
                stylesheet: stylesheet
            } 
        } catch(e) {
            return { message: `Data processing failed with error: ${e.message}`}
        }
    }

    getStylesheet() {
        return {
            "appli": {
                "name": "Datasets Relationship",
                "debug": true
            },
            "node": {
                "radius": {
                    "variable": "qtItems",
                    "scale": "linear"
                },
                "default": {
                    "color": "steelblue",
                    "label": this.prettyTitle(this.filters.source)
                },
                "mix": {
                    "color": "yellow",
                    "active": true
                },
                "member": {
                    "color": "purple"
                },
                "other": {
                    "color": "green"
                },
                "fst": {
                    "color": "lightgreen",
                    "priority": 1,
                    "label": this.prettyTitle(this.filters.source)
                },
                "snd": {
                    "color": "orange",
                    "priority": 2,
                    "label": this.prettyTitle(this.filters.target)
                },
                "rst": {
                    "color": "purple",
                    "priority": 3
                }
            },
            "barchart": {
                "x": {
                    "title": "Last Modified"
                }
            },
            "edge": {
                "color": "green"
            },
            "services": [
                {
                    "label": "See it on HuggingFace",
                    "url": "https://huggingface.co/datasets/"
                }
            ]
        }
    }

}

async function test() {
    // Example usage
    const folderPath = 'data/modality_datasets';
    const dataTools = new DataTools(folderPath);

    let filters = {
        modality: [ 'text' ],
        task_categories: [],
        task_ids: [],
        license: [ 'mit' ],
        size_categories: [],
        format: [],
        language: [],
        created_at: [ ],
        downloads: [  ],
        last_modified: [ ],
        likes: [ ],
        link: "language",
        source: 'dataset',
        target: 'task_categories',
        theme: 'license'
    }

    // await dataTools.init('filters', filters)

    await dataTools.init('datavis', filters)
    let result = await dataTools.getData()
    console.log(result)
    console.log("result = ", result.data.length, result.data.splice(0,2))
    
    // let network = await dataTools.createDatasetNetwork();
    // console.log(network.data.slice(0,2))
    
}
// test()
module.exports = DataTools
