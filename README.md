#DataLens

DataLens is a web-based platform that combines faceted search with advanced visualization techniques to enhance resource discovery and exploration. It supports network-based visualizations, where graph structures are dynamically adapted to suit specific analysis tasks. Additionally, DataLens implements a chained-views approach, allowing users to interact with data from multiple perspectives.

🌐 Live Demo: https://dataviz.i3s.unice.fr/datalens/

📁 Repository Structure
Here's a breakdown of the main directories in this repository:

public/
Contains core HTML files related to the design and layout of the website.

scripts/
Includes utility scripts for data preparation:

fetch_datasets.py: Queries the Hugging Face API to extract dataset and model metadata.

Additional scripts: Used to split datasets by modality to support more efficient faceted search and exploration.

view/
Contains the main JavaScript files responsible for rendering interactive visualizations. This includes the logic for building network structures and managing the chained-view navigation.

CITING DATALENS
If you use this tool we kindly ask you to include a reference to the paper below.

TBA

