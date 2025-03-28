from huggingface_hub import HfApi
import json
from datetime import datetime

# Instantiate HfApi client
hf_api = HfApi(
    endpoint="https://huggingface.co", # This is the default endpoint.
    token="API TOKEN", # Your token here.
)

# # List datasets using HfApi client
# datasets = hf_api.list_datasets()

# # Convert datasets generator to a list of dictionaries
# datasets_list = [dataset.__dict__ for dataset in datasets]

# # Custom serialization function for JSON
# def custom_serializer(obj):
#     if isinstance(obj, datetime):
#         return obj.isoformat()
#     raise TypeError(f"Type {type(obj)} not serializable")

# # Save the list of dictionaries to a JSON file
# with open('datasets_new.json', 'w') as json_file:
#     json.dump(datasets_list, json_file, indent=4, default=custom_serializer)

# print("Datasets saved to datasets.json")

# List datasets using HfApi client
datasets = hf_api.list_models()

# Convert datasets generator to a list of dictionaries
datasets_list = [dataset.__dict__ for dataset in datasets]

# Custom serialization function for JSON
def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Save the list of dictionaries to a JSON file
with open('models_new.json', 'w') as json_file:
    json.dump(datasets_list, json_file, indent=4, default=custom_serializer)

print("Datasets saved to datasets.json")
