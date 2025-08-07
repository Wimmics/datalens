# DataLens

DataLens is a web-based platform that combines faceted search with advanced visualization techniques to enhance resource discovery and exploration. It supports network-based visualizations, where graph structures are dynamically adapted to suit specific analysis tasks. Additionally, DataLens implements a chained-views approach, allowing users to interact with data from multiple perspectives.

🌐 Live Demo: https://dataviz.i3s.unice.fr/datalens/

## Features

- **Faceted Search**: Advanced filtering capabilities for efficient data exploration
- **Network Visualizations**: Dynamic graph structures adapted for specific analysis tasks
- **Chained Views**: Multi-perspective data interaction approach
- **Knowledge Graph Integration**: RDF-based data storage and SPARQL querying
- **Real-time Data Processing**: Automated data lifting and transformation pipelines

## 📁 Repository Structure

This repository is organized into several key components:

### `/case-study/`
Contains data and analysis for specific use cases:
- `data/input/` - Raw input datasets
- `data/output/` - Processed RDF data in Turtle format
- `lifting/scripts/` - Data transformation and lifting scripts

### `/corese-server/`
Corese RDF server setup for SPARQL query processing:
- Docker-based deployment configuration
- Build scripts for containerized RDF processing

### `/ontology/`
RDF ontologies and vocabularies:
- `mluo.ttl` - Machine Learning Use-case Ontology (MLUO)
- `used-vocabularies/` - Standard vocabularies (BIBO, DCAT3, DCTERMS, ISO639-1, PROV-O)

### `/virtuoso-server/`
OpenLink Virtuoso RDF database server:
- Docker Compose setup for RDF triple store
- Automated data loading and configuration
- SPARQL endpoint for data querying

### `/vis/`
Web-based visualization interface:
- `server.js` - Node.js backend server
- `datatools.js` - Data processing utilities
- `public/` - Frontend assets (CSS, JS, images)
- `views/` - HTML templates and view components
- `sparql-filters/` - SPARQL query templates for filtering
- `sparql-mge/` - SPARQL queries for data extraction
- `cache/` - Cached query results for performance

### `/sparql-examples/`
Example SPARQL queries for common operations:
- Dataset counting and analysis queries
- Sample queries for data exploration

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js (for the visualization server)
- Git

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/amenin/datalens.git
   cd datalens
   ```

2. **Start the RDF database:**
   ```bash
   cd virtuoso-server
   ./build-virtuoso-server.sh
   ```

3. **Start the visualization server:**
   ```bash
   cd vis
   npm install
   node server.js
   ```

4. **Access the application:**
   - Main interface: http://localhost:3000
   - SPARQL endpoint: http://localhost:8890/sparql

## 🔧 Architecture

DataLens follows a modular architecture:

1. **Data Layer**: Virtuoso RDF database stores semantic data
2. **Processing Layer**: Data lifting scripts convert raw data to RDF
3. **Query Layer**: SPARQL endpoints provide data access
4. **Visualization Layer**: Web interface with interactive visualizations
5. **Ontology Layer**: MLUO and standard vocabularies define data semantics

## 📊 Data Pipeline

1. **Data Ingestion**: Raw datasets are processed through lifting scripts
2. **RDF Conversion**: Data is transformed into RDF using MLUO ontology
3. **Storage**: RDF triples are loaded into Virtuoso database
4. **Querying**: SPARQL queries extract data for visualization
5. **Visualization**: Interactive web interface presents data insights

## 🛠️ Development

### Adding New Data Sources
TBA

## 📚 Documentation

- [Virtuoso Server Setup](virtuoso-server/README.md)
- [Corese Server Configuration](corese-server/README.md)
- [Ontology Documentation](ontology/)

## 🎯 Use Cases

DataLens is designed for:
- **Machine Learning Dataset Discovery**: Find relevant datasets for ML tasks
- **Research Data Exploration**: Navigate complex research datasets
- **Knowledge Graph Visualization**: Explore semantic relationships
- **Faceted Search Applications**: Build advanced filtering interfaces

## 📄 Cite this work

If you use DataLens in your research, please cite:

```
TBA - Paper reference to be added
```

## 📝 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.


