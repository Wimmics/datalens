# Corese Server

This directory contains the configuration and scripts for setting up a Corese RDF server using Docker. Corese is a software platform implementing and extending the standards of the Semantic Web, providing SPARQL query processing, reasoning capabilities, and RDF data management.

## Overview

The Corese server setup includes:
- Docker Compose configuration for the Wimmics Corese platform
- Automated data preparation and loading script
- Integration with DataLens ontologies and case study data
- SPARQL endpoint for querying RDF data

## Prerequisites

- Docker and Docker Compose installed
- `wimmics/corese` docker image installed. See [Corese docs](https://wimmics.github.io/corese/docker/README.html).
- Access to the parent directory structure containing:
  - `../ontology/` - Contains MLUO ontology and vocabulary files
  - `../case-study/data/output/` - Contains generated RDF data files

## Quick Start

1. **Build and start the Corese server:**
   ```bash
   ./build-corese-server.sh
   ```

2. **Access the Corese interface:**
   - Web interface: http://localhost:8050
   - SPARQL endpoint: http://localhost:8050/sparql

## What the Setup Does

The `build-corese-server.sh` script performs the following operations:

1. **Data Preparation:**
   - Creates and cleans the `corese-data/` directory
   - Copies case study output files from `../case-study/data/output/`
   - Copies vocabulary files from `../ontology/used-vocabularies/`
   - Copies the MLUO ontology (`../ontology/mluo.ttl`)

2. **Directory Structure:**
   - Creates `config/` directory for Corese configuration files
   - Creates `log/` directory for server logs
   - Ensures all directories are clean before setup

3. **Container Management:**
   - Starts the Corese container using Docker Compose
   - Waits for initialization (15 seconds)
   - Restarts the container to ensure proper data loading

## Configuration

### Docker Compose
- **Image:** `wimmics/corese`
- **Container name:** `corese-datalens`
- **Platform:** `linux/amd64` (for compatibility)
- **Port:** `8050` (mapped from container port `8080`)

### Volumes
The following directories are mounted into the container:
- `./corese-data/` → `/usr/local/corese/data` (RDF data files)
- `./config/` → `/usr/local/corese/config` (configuration files)
- `./log/` → `/usr/local/corese/log` (server logs)

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

### Web Interface
Access the Corese web interface at http://localhost:8050 to:
- Browse loaded RDF data
- Execute SPARQL queries interactively
- Explore the knowledge graph structure
- Access reasoning capabilities

### SPARQL Endpoint
Send SPARQL queries to: http://localhost:8050/sparql

### Example SPARQL Query
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?predicate ?object
WHERE {
  ?subject ?predicate ?object .
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
docker-compose logs -f corese
```

### Restart the server:
```bash
docker-compose restart corese
```

### Access container shell:
```bash
docker exec -it corese-datalens /bin/bash
```

## Features

### Corese Capabilities
- **SPARQL 1.1 Query**: Full SPARQL query language support
- **SPARQL 1.1 Update**: Data modification capabilities
- **RDF Reasoning**: Built-in inference engine
- **Rule-Based Reasoning**: Custom rule definition and execution
- **SHACL Validation**: Shape Constraint Language support
- **RDF/RDFS/OWL**: Support for semantic web standards

### Integration Benefits
- **Reasoning Engine**: Automatic inference of implicit knowledge
- **Advanced Querying**: Complex SPARQL queries with reasoning
- **Data Validation**: SHACL-based constraint checking
- **Performance**: Optimized for large RDF datasets

## Troubleshooting

### Container won't start
- Check if port 8050 is available
- Verify Docker and Docker Compose are running
- Check logs: `docker-compose logs corese`

### Data not loaded
- Ensure source directories exist and contain valid RDF files
- Check that the build script completed without errors
- Verify container has write access to mounted volumes

### Web interface not accessible
- Wait for container initialization (may take up to 30 seconds)
- Check container status: `docker-compose ps`
- Verify port 8050 is not blocked by firewall

### Performance issues
- Monitor container resources: `docker stats corese-datalens`
- Check log files in the `log/` directory
- Consider increasing container memory limits if needed

## File Structure

```
corese-server/
├── build-corese-server.sh    # Main setup script
├── docker-compose.yml        # Docker Compose configuration
├── README.md                 # This file
├── corese-data/             # RDF data directory (auto-generated)
│   ├── *.ttl               # Vocabulary and ontology files
│   └── output_batch_*.ttl  # Case study output files
├── config/                  # Corese configuration (auto-generated)
└── log/                     # Server logs (auto-generated)
```
