import json
import os
import re
from collections import defaultdict
from pathlib import Path


PREFIXES = """@prefix mluo: <http://example.org/mluo/ontology#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/mluo/resource/> .

"""


def sanitize_fragment(value):
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value))


def quote_literal(value):
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def extract_tag_values(tags, prefix):
    needle = f"{prefix}:"
    values = []
    for tag in tags or []:
        if isinstance(tag, str) and tag.startswith(needle):
            values.append(tag[len(needle):])
    return values


def maybe_xsd_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "T" not in text:
        return None
    return f'{quote_literal(text)}^^xsd:dateTime'


def nested_dict(value):
    return value if isinstance(value, dict) else {}


def build_dataset_ttl(entry):
    dataset_id = entry.get("id") or entry.get("_id")
    if not dataset_id:
        return ""

    resource_id = sanitize_fragment(dataset_id)
    tags = entry.get("tags", [])
    distributions = []
    usage_nodes = []
    entity_blocks = []

    lines = [
        f"ex:dataset_{resource_id} a dcat:Dataset ;",
        f"    dct:identifier {quote_literal(dataset_id)} ;",
    ]

    card_data = nested_dict(entry.get("cardData"))
    dataset_info = nested_dict(card_data.get("dataset_info"))
    title = dataset_info.get("dataset_name") or entry.get("id")
    if title:
        lines.append(f"    dct:title {quote_literal(title)} ;")

    downloads = entry.get("downloads")
    if isinstance(downloads, int):
        lines.append(f"    mluo:downloadCount {downloads} ;")

    likes = entry.get("likes")
    if isinstance(likes, int):
        lines.append(f"    mluo:likesCount {likes} ;")

    issued = maybe_xsd_datetime(entry.get("createdAt") or entry.get("created_at"))
    if issued:
        lines.append(f"    dct:issued {issued} ;")

    modified = maybe_xsd_datetime(entry.get("lastModified") or entry.get("last_modified"))
    if modified:
        lines.append(f"    dct:modified {modified} ;")

    for size in extract_tag_values(tags, "size_categories"):
        lines.append(f"    mluo:rowsSize {quote_literal(size)} ;")

    for idx, modality in enumerate(extract_tag_values(tags, "modality")):
        mod_id = sanitize_fragment(modality)
        lines.append(f"    mluo:hasModality ex:modality_{mod_id} ;")
        if idx == 0:
            entity_blocks.append(
                f"ex:modality_{mod_id} a mluo:Modality ;\n"
                f"    skos:prefLabel {quote_literal(modality)} .\n"
            )

    for lang in extract_tag_values(tags, "language"):
        lang_id = sanitize_fragment(lang)
        lines.append(f"    dct:language ex:language_{lang_id} ;")
        entity_blocks.append(
            f"ex:language_{lang_id} skos:prefLabel {quote_literal(lang)}@en .\n"
        )

    format_values = extract_tag_values(tags, "format")
    license_values = extract_tag_values(tags, "license")
    if format_values or license_values:
        dist_id = f"distribution_{resource_id}"
        distributions.append(f"ex:{dist_id}")
        for fmt in format_values:
            fmt_id = sanitize_fragment(fmt)
            entity_blocks.append(
                f"ex:format_{fmt_id} a dct:MediaTypeOrExtent ;\n"
                f"    rdfs:label {quote_literal(fmt)} .\n"
            )
            entity_blocks.append(f"ex:{dist_id} dct:format ex:format_{fmt_id} .\n")
        for license_name in license_values:
            lic_id = sanitize_fragment(license_name)
            entity_blocks.append(
                f"ex:license_{lic_id} a dct:LicenseDocument ;\n"
                f"    rdfs:label {quote_literal(license_name)} .\n"
            )
            entity_blocks.append(f"ex:{dist_id} dct:license ex:license_{lic_id} .\n")

    task_values = extract_tag_values(tags, "task_ids")
    task_categories = extract_tag_values(tags, "task_categories")
    if task_values or task_categories:
        usage_id = f"usage_{resource_id}"
        usage_nodes.append(f"ex:{usage_id}")
        for task in task_values:
            task_id = sanitize_fragment(task)
            entity_blocks.append(
                f"ex:task_{task_id} a mluo:Task ;\n"
                f"    rdfs:label {quote_literal(task)} .\n"
            )
            entity_blocks.append(f"ex:{usage_id} mluo:hasTask ex:task_{task_id} .\n")
        for category in task_categories:
            category_id = sanitize_fragment(category)
            entity_blocks.append(
                f"ex:taskcategory_{category_id} a mluo:TaskCategory ;\n"
                f"    rdfs:label {quote_literal(category)} .\n"
            )
            entity_blocks.append(f"ex:{usage_id} mluo:hasTaskCategory ex:taskcategory_{category_id} .\n")

    for distribution in distributions:
        lines.append(f"    dcat:distribution {distribution} ;")

    for usage in usage_nodes:
        lines.append(f"    mluo:hasUsage {usage} ;")

    if lines[-1].endswith(";"):
        lines[-1] = lines[-1][:-1] + " ."

    return "\n".join(lines) + "\n\n" + "".join(entity_blocks)


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
        safe_modality = modality.replace('/', '_').replace(' ', '_')
        output_file_path = os.path.join(output_directory, f"{safe_modality}.json")
        with open(output_file_path, 'w', encoding='utf-8') as file:
            json.dump(datasets, file, indent=4)
    
    return datasets_by_modality


def write_ttl_by_modality(datasets_by_modality, output_directory):
    for modality, datasets in datasets_by_modality.items():
        safe_modality = modality.replace('/', '_').replace(' ', '_')
        ttl_file_path = Path(output_directory) / f"{safe_modality}.ttl"

        with ttl_file_path.open('w', encoding='utf-8') as file:
            file.write(PREFIXES)
            for entry in datasets:
                ttl_chunk = build_dataset_ttl(entry)
                if ttl_chunk:
                    file.write(ttl_chunk)

# Example usage
BASE_DIR = Path(__file__).resolve().parents[2]
json_file_path = BASE_DIR / 'data' / 'input' / 'datasets_new.json'
output_directory = BASE_DIR / 'data' / 'output'

datasets_by_modality = split_datasets_by_modality(json_file_path, output_directory)
write_ttl_by_modality(datasets_by_modality, output_directory)

print(f"Datasets JSON and TTL files have been generated in '{output_directory}'.")
