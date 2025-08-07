const express = require('express')
const fs = require("fs")
const bodyParser = require('body-parser')
const path = require('path')
const https = require('https')
const crypto = require('crypto');
const os = require('os');

const util = require('util');
const exec = util.promisify(require('child_process').exec);

require('dotenv').config({ path: require('path').resolve(__dirname, '.env') });

const app = express()
// Pour accepter les connexions cross-domain (CORS)
app.use(function (req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
    next();
});

app.set('view engine', 'ejs')
app.set('views', path.join(__dirname, 'views'))

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

const prefix = '/datalens'

app.use(prefix, express.static(path.join(__dirname, 'public')))

// Serve static files from 'node_modules' (optional: use a prefix to avoid conflicts)
app.use(prefix + '/node_modules', express.static(path.join(__dirname, 'node_modules')));


app.get(prefix, (req, res) => {
    res.render('about')
})

app.get(prefix + '/explorer', (req, res) => {
    res.render('index')
})

// Hash function
function hash(...args) {
    return crypto.createHash('sha256').update(args.join('--')).digest('hex');
}

async function getCoreseCommand(query, inputPath) {

    let dataPath = path.resolve(__dirname, inputPath)
    if (!fs.existsSync(dataPath)) {
        return { error: `Data path does not exist: ${dataPath}` }
    }

    let ontologyPath = path.resolve(__dirname, process.env.ONTOLOGY_TTL)
    if (!fs.existsSync(ontologyPath)) {
        return { error: `Ontology path does not exist: ${ontologyPath}` }
    }

    let prov = process.env.PROV_TTL ? path.resolve(__dirname, process.env.PROV_TTL) : "https://www.w3.org/ns/prov-o.ttl";
    let dcat = process.env.DCAT_TTL ? path.resolve(__dirname, process.env.DCAT_TTL) : "https://www.w3.org/ns/dcat3.ttl";
    let bibo = process.env.BIBO_TTL ? path.resolve(__dirname, process.env.BIBO_TTL) : "https://www.dublincore.org/specifications/bibo/bibo/bibo.ttl";
    let dcterms = process.env.DCTERMS_TTL ? path.resolve(__dirname, process.env.DCTERMS_TTL) : "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl";

    let cmd = [
        'corese query',
        `-q ${query}`, // The SPARQL query file
        `-i ${dataPath}`,
        `-i ${ontologyPath}`,
        `-i ${prov}`,
        `-i ${dcat}`,
        `-i ${bibo}`,
        `-i ${dcterms}`,
        '-if ttl',
        '-of json'
      ]

    let iso6391 = path.resolve(__dirname, process.env.ISO639_1_TTL);

    if (!fs.existsSync(iso6391)) {
        console.warn(`Warning: ISO639_1_TTL file does not exist: ${iso6391}. Continuing without it.`);
    } else {
        cmd.push(`-i ${iso6391}`)
    }

    return cmd.join(' ');
}

async function execCommand(cmd) {
    try {
        const { stdout, stderr } = await exec(cmd, { maxBuffer: 1024 * 1024 * 20 });

        if (stderr) {
            console.error(`stderr: ${stderr}`);
            return { error: `stderr: ${stderr}` };
        }

        try {
            return JSON.parse(stdout);
        } catch (e) {
            return { error: `Failed to parse JSON: ${e.message}\nRaw output:\n${stdout}` };
        }
    } catch (error) {
        console.error(`exec error: ${error}`);
        return { error: error.message };
    }
}

app.get(prefix + '/sparql-filters/config.json', (req, res) => {
    const configPath = process.env.SPARQL_FILTERS_PATH
    
    if (!configPath) {
        return res.status(500).json({ error: 'SPARQL_FILTERS_PATH environment variable is not set.' });
    }

    let configFile = path.resolve(__dirname, configPath, 'config.json');
    if (!fs.existsSync(configFile)) {
        return res.status(404).json({ error: `Configuration file not found: ${configFile}` });
    }

    res.sendFile(configFile)
});

app.get(prefix + "/sparql-filters/query-endpoint/:queryFile", async (req, res) => {
    const queryFile = req.params.queryFile; // The query file name
    console.log(`Received request for query file: ${queryFile}`);

    // Sanitize the filename to prevent command injection (basic check)
    if (!/^[\w.-]+$/.test(queryFile)) {
        res.status(500).json({ error: 'Invalid query file name' })
    }

    let filtersFolder = process.env.SPARQL_FILTERS_PATH
    if (!filtersFolder) {
        return res.status(500).json({ error: 'SPARQL_FILTERS_PATH environment variable is not set.' });
    }

    const cacheFolder = path.join(__dirname, filtersFolder, 'cache');
    if (!fs.existsSync(cacheFolder)) {
        fs.mkdirSync(cacheFolder, { recursive: true });
    }

    // Create a unique cache file name based on the query
    let cacheFile = path.resolve(__dirname, cacheFolder, `${hash(queryFile)}.json`); 
    if (fs.existsSync(cacheFile)) {
        return res.sendFile(cacheFile);
    }

    let queryfilePath = path.join(__dirname, filtersFolder, queryFile);
    if (!fs.existsSync(queryfilePath)) {        
        return res.status(404).json({ error: `Query file not found: ${queryfilePath}` });
    }

    let query = fs.readFileSync(queryfilePath, 'utf-8');
    console.log(`Query file content: ${query}`);
    let endpointUrl = process.env.SPARQL_ENDPOINT_URL;
    if (!endpointUrl) {
        return res.status(500).json({ error: 'SPARQL_ENDPOINT_URL environment variable is not set.' });
    }

    let url = `${endpointUrl}?query=${encodeURIComponent(query)}`;
    let json = await fetch(url, {headers: { 'Accept': 'application/sparql-results+json' } })
        .then(response => {
            if (!response.ok) {
                return { error: `HTTP error! status: ${response.statusText}` }
            }
            return response.json()
        })
        .catch(error => {
            console.error(`Error fetching from SPARQL endpoint: ${error.message}`);     
            return { error: `Error fetching from SPARQL endpoint: ${error.message}` };
        });

    if (json.error) {
        return res.status(500).json({ error: json.error });
    }

    // Write the result to the cache file
    fs.writeFileSync(cacheFile, JSON.stringify(json, null, 2), 'utf-8');

    // Send the JSON response
    res.json(json)

})

app.get(prefix + "/sparql-filters/corese-query/:queryFile", async (req, res) => {
    const queryFile = req.params.queryFile; // The query file name
    console.log(`Received request for query file: ${queryFile}`);

    // Sanitize the filename to prevent command injection (basic check)
    if (!/^[\w.-]+$/.test(queryFile)) {
        res.status(500).json({ error: 'Invalid query file name' })
    }

    let filtersFolder = process.env.SPARQL_FILTERS_PATH
    if (!filtersFolder) {
        return res.status(500).json({ error: 'SPARQL_FILTERS_PATH environment variable is not set.' });
    }

    const cacheFolder = path.join(__dirname, filtersFolder, 'cache');
    if (!fs.existsSync(cacheFolder)) {
        fs.mkdirSync(cacheFolder, { recursive: true });
    }

    // Create a unique cache file name based on the query
    let cacheFile = path.resolve(__dirname, cacheFolder, `${hash(queryFile)}.json`); 
    if (fs.existsSync(cacheFile)) {
        return res.sendFile(cacheFile);
    }

    let queryfilePath = path.join(__dirname, filtersFolder, queryFile);
    if (!fs.existsSync(queryfilePath)) {        
        return res.status(404).json({ error: `Query file not found: ${queryfilePath}` });
    }

    let cmd = await getCoreseCommand(queryfilePath, process.env.KG_FOLDER_PATH);

    if (cmd.error) {
        return res.status(500).json({ error: cmd.error });
    }

    let json = await execCommand(cmd);

    if (json.error) {
        return res.status(500).json({ error: json.error });
    }

    // Write the result to the cache file
    fs.writeFileSync(cacheFile, JSON.stringify(json, null, 2), 'utf-8');

    // Send the JSON response
    res.json(json)

})

app.get(prefix + '/sparql-mge/config.json', (req, res) => {
    const configPath = process.env.SPARQL_MGE_PATH

    if (!configPath) {
        return res.status(500).json({ error: 'SPARQL_FILTERS_PATH environment variable is not set.' });
    }

    let configFile = path.resolve(__dirname, configPath, 'config.json');
    if (!fs.existsSync(configFile)) {
        return res.status(404).json({ error: `Configuration file not found: ${configFile}` });
    }

    res.sendFile(configFile)
})

app.get(prefix + '/sparql-mge/config/:queryFile', async (req, res) => {
    const queryFile = req.params.queryFile; // The SPARQL query file name
    console.log(`Received request for SPARQL query file: ${queryFile}`);

    // Sanitize the filename to prevent command injection (basic check)
    if (!/^[\w.-]+$/.test(queryFile)) {
        return res.status(500).json({ error: 'Invalid query file name' });
    }

    let configFolder = process.env.SPARQL_MGE_PATH
    if (!configFolder) {
        return res.status(500).json({ error: 'SPARQL_MGE_PATH environment variable is not set.' });
    }   

    res.sendFile(path.resolve(__dirname, configFolder, queryFile))
})

app.post(prefix + '/sparql-mge/query', async (req, res) => {
    const query = req.body.query; // The SPARQL query string
    const batchMode = req.body.batch; // Whether to run in batch mode or not

    if (!query) {
        return res.status(400).json({ error: 'Missing query parameter' });
    }

    let cacheFolder = path.resolve(__dirname, 'cache');
    if (!fs.existsSync(cacheFolder)) {
        fs.mkdirSync(cacheFolder, { recursive: true });
    }

    // Create a unique cache file name based on the query
    let cacheFile = path.resolve(__dirname, cacheFolder, `${hash(query)}.json`);
    console.log(`Cache file path: ${cacheFile}`);

    // Check if the cache file exists
    if (fs.existsSync(cacheFile)) {
        return res.sendFile(cacheFile);
    }

    let dataPath = process.env.KG_FOLDER_PATH;

    // Create a temporary file for the query
    const tempQueryPath = path.join(os.tmpdir(), `corese_query_${Date.now()}.rq`);
    fs.writeFileSync(tempQueryPath, query, 'utf-8');

    // If batch mode is enabled, we need to read the query from a file
    let result = []
    if (batchMode) {
        console.log(`Running in batch mode`);
        const files = fs.readdirSync(dataPath)
            .filter(file => file.endsWith('.ttl'));

        for (const file of files) {
            let cmd = await getCoreseCommand(tempQueryPath, path.join(dataPath, file))
            if (cmd.error) {
                return res.status(500).json({ error: `Error getting command for query: ${cmd.error}` });
            }

            let json = await execCommand(cmd); 
            if (json.error) {
                return res.status(500).json({ error: `Error executing command: ${json.error}` });
            }

            let bindings = json.results.bindings;
            if (!bindings || bindings.length === 0) {
                console.warn(`Batch ${file}: no results found.`);
                continue; // Skip to the next batch if no results
            }

            console.log(`Batch ${file}: done.`);
            result.push(...bindings);
        }
    }
    // If batch mode is not enabled, we run the query on the main data path
    else {
        let cmd = await getCoreseCommand(tempQueryPath, dataPath);
        if (cmd.error) {
            return res.status(500).json({ error: `Error getting command for query: ${cmd.error}` });
        }

        let json = await execCommand(cmd) 
        if (json.error) {
            return res.status(500).json({ error: `Error executing command: ${json.error}` });
        }
        
        let bindings = json.results.bindings;
        if (!bindings || bindings.length === 0) {
            return res.status(404).json({ error: `No results found for query: ${query}` });
        }

        result = [...bindings]
    }

    try {// Save to cache file
        fs.writeFileSync(cacheFile, JSON.stringify(result, null, 2), 'utf-8');
    } catch (error) {
        console.error(`Error writing to cache file: ${error.message}`);
        //return res.status(500).json({ error: `Error writing to cache file: ${error.message}` });
    }

    if(tempQueryPath) fs.unlinkSync(tempQueryPath); // Clean up temp file

    // Send result as JSON response
    res.status(200).json(result)
    
})

app.post(prefix + '/sparql-mge/query-endpoint', async (req, res) => {
    const query = req.body.query; // The SPARQL query string

    if (!query) {
        return res.status(400).json({ error: 'Missing query parameter' });
    }

    let cacheFolder = path.resolve(__dirname, 'cache');
    if (!fs.existsSync(cacheFolder)) {
        fs.mkdirSync(cacheFolder, { recursive: true });
    }

    // Create a unique cache file name based on the query
    let cacheFile = path.resolve(__dirname, cacheFolder, `${hash(query)}.json`);
    console.log(`Cache file path: ${cacheFile}`);

    // Check if the cache file exists
    if (fs.existsSync(cacheFile)) {
        return res.sendFile(cacheFile);
    }

    let endpointUrl = process.env.SPARQL_ENDPOINT_URL;
    if (!endpointUrl) {
        return res.status(500).json({ error: 'SPARQL_ENDPOINT_URL environment variable is not set.' });
    }
    
    let url = `${endpointUrl}?query=${encodeURIComponent(query)}`;
    let json = await fetch(url, {headers: { 'Accept': 'application/sparql-results+json' } })
        .then(response => response.json())
        .catch(error => {
            console.error(`Error fetching from SPARQL endpoint: ${error.message}`);
            return { error: `Error fetching from SPARQL endpoint: ${error.message}` };
        });
    
    if (json.error) {
        return res.status(500).json({ error: json.error });
    }
    
    let bindings = json.results.bindings;
    if (!bindings || bindings.length === 0) {
        return res.status(404).json({ error: `No results found for query: ${query}` });
    }

    try {// Save to cache file
        fs.writeFileSync(cacheFile, JSON.stringify(bindings, null, 2), 'utf-8');
    } catch (error) {
        console.error(`Error writing to cache file: ${error.message}`);
        //return res.status(500).json({ error: `Error writing to cache file: ${error.message}` });
    }

    // Send result as JSON response
    res.status(200).json(bindings)
    
})




// Start HTTP
try {
    app.listen(process.env.PORT_HTTP, () => {
        console.log(`✅ HTTP Server started on port ${process.env.PORT_HTTP}`);
    });
} catch (e) {
    console.error("⚠️ Could not start HTTP server:", e.message);
}

// Start HTTPS
try {
    const certPath = process.env.CERT_FOLDER;
    const options = {
        key: fs.readFileSync(path.join(certPath, process.env.CERT_KEY)),
        cert: fs.readFileSync(path.join(certPath, process.env.CERT_CERT)),
    };

    https.createServer(options, app).listen(process.env.PORT_HTTPS, () => {
        console.log(`✅ HTTPS Server started on port ${process.env.PORT_HTTPS}`);
    });
} catch (e) {
    console.log("⚠️ Could not start HTTPS server:", e.message);
}
