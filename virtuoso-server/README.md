# Virtuoso Server

This directory contains the configuration and scripts for setting up a Virtuoso RDF database server using Docker. The server is used to store and query RDF data as part of the DataLens project.

## Overview

The Virtuoso server setup includes:
- Docker Compose configuration for OpenLink Virtuoso Open Source 7
- Automated data loading script
- Custom Virtuoso configuration
- RDF data from ontologies and case study outputs

## Prerequisites

- Docker and Docker Compose installed
- `openlink/virtuoso-opensource-7` Docker image installed. 
    - See the docker documentation for virtuoso [here](https://hub.docker.com/r/openlink/virtuoso-opensource-7).
- Access to the parent directory structure containing:
  - `../ontology/` - Contains MLUO ontology and vocabulary files
  - `../case-study/data/output/` - Contains generated RDF data files

## Quick Start

1. **Build and start the Virtuoso server:**
   ```bash
   ./build-virtuoso-server.sh
   ```

2. **Access the SPARQL endpoint:**
   - Web interface: http://localhost:8890/sparql
   - Direct endpoint: http://localhost:8890/sparql

## What the Setup Does

The `build-virtuoso-server.sh` script performs the following operations:

1. **Data Preparation:**
   - Creates a clean `virtuoso-data/` directory
   - Copies vocabulary files from `../ontology/used-vocabularies/`
   - Copies the MLUO ontology (`../ontology/mluo.ttl`)
   - Processes and cleans TTL files from case study output data

2. **Data Cleaning:**
   - Removes invalid XML control characters from TTL files
   - Preserves essential characters (tab, LF, CR)

3. **Container Management:**
   - Stops any existing Virtuoso container
   - Starts a new container using Docker Compose

4. **Data Loading:**
   - Waits for Virtuoso to be ready
   - Registers all TTL files in the database
   - Loads RDF data into the graph: `http://example.org/data`

## Configuration

### Docker Compose
- **Image:** `openlink/virtuoso-opensource-7`
- **Container name:** `virtuoso-datalens`
- **Ports:**
  - `8890`: SPARQL endpoint and web UI
  - `1111`: ISQL command line interface
- **Default credentials:** Username: `dba`, Password: `dba`

### Volumes
Transfer a configuration file allowing access to the data directory
- `./virtuoso.ini` → `/opt/virtuoso-opensource/virtuoso.ini`

Transfer the data (auto-generated folder) to the container
- `./virtuoso-data/` → `/data/`

### Data Sources
The following data is automatically loaded:

**Vocabularies:**
- BIBO (Bibliographic Ontology)
- DCAT 3 (Data Catalog Vocabulary)
- DCTERMS (Dublin Core Terms)
- ISO 639-1 (Language codes)
- PROV-O (Provenance Ontology)

**Project Data:**
- MLUO ontology (`mluo.ttl`)
- Case study output batches (`output_batch_*.ttl`)

## Usage

### SPARQL Queries
Once the server is running, you can execute SPARQL queries through:

1. **Web Interface:** Navigate to http://localhost:8890/sparql
2. **HTTP POST:** Send queries to the endpoint
3. **Command Line:** Use `isql` through Docker:
   ```bash
   docker exec -it virtuoso-datalens isql 1111 dba dba
   ```

### Example SPARQL Query
```sparql
SELECT ?s ?p ?o 
FROM <http://example.org/data>
WHERE {
  ?s ?p ?o .
} 
LIMIT 10
```

## Management Commands

### Stop the server:
```bash
docker-compose down
```

### View logs:
```bash
docker-compose logs -f virtuoso
```

### Restart the server:
```bash
docker-compose restart virtuoso
```

### Access ISQL interface:
```bash
docker exec -it virtuoso-datalens isql 1111 dba dba
```

## Data Graph

All RDF data is loaded into the named graph: `http://example.org/data`

To query data from this specific graph, use:
```sparql
SELECT ?s ?p ?o 
FROM <http://example.org/data>
WHERE {
  ?s ?p ?o .
}
```

## Troubleshooting

### Container won't start
- Check if ports 8890 and 1111 are available
- Verify Docker and Docker Compose are running
- Check logs: `docker-compose logs virtuoso`

### Data not loaded
- Ensure source directories exist and contain TTL files
- Check that TTL files are valid RDF
- Verify the build script completed without errors

### Connection refused
- Wait for the healthcheck to pass (may take up to 60 seconds)
- Check container status: `docker-compose ps`

## File Structure

```
virtuoso-server/
├── build-virtuoso-server.sh  # Main setup script
├── docker-compose.yml        # Docker Compose configuration
├── virtuoso.ini             # Virtuoso server configuration
├── README.md                # This file
└── virtuoso-data/           # RDF data directory (auto-generated)
    ├── *.ttl               # Vocabulary and ontology files
    └── output_batch_*.ttl  # Case study output files
```

## Security Notes

- Default credentials are used (dba/dba) - change for production use
- Server is accessible on localhost only by default
- Consider firewall rules if exposing externally