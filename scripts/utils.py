import json
import os
from collections import defaultdict

def split_datasets_by_modality(json_file_path, output_directory):
    # Ensure the output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Dictionary to store datasets by modality
    datasets_by_modality = defaultdict(list)
    
    # Filter datasets by modality
    for entry in data:
        modalities = [tag.split("modality:")[1] for tag in entry.get('tags', []) if tag.startswith("modality:")]
        if modalities:
            for modality in modalities:
                datasets_by_modality[modality].append(entry)
    
    # Write each modality's datasets to a separate JSON file
    for modality, datasets in datasets_by_modality.items():
        output_file_path = os.path.join(output_directory, f"{modality}.json")
        with open(output_file_path, 'w') as file:
            json.dump(datasets, file, indent=4)
    
    return datasets_by_modality

# Example usage
json_file_path = 'datasets_models.json'
output_directory = 'modality_datasets'

datasets_by_modality = split_datasets_by_modality(json_file_path, output_directory)

print(f"Datasets have been split by modality and stored in the '{output_directory}' directory.")
