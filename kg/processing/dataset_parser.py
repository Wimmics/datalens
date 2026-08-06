import argparse
import json
from pathlib import Path
from typing import Any
from ...kaggle_kg.processing.canonical_thesaurus import canonicalize, get_canonical_tag_alone
from ...kaggle_kg.processing.parser_tools import (
    build_uris, dedupe, get_tag_alone, get_tag_with_prefix, hash16,
    normalize_boolean, normalize_string, paper_url, split_hf_values
)


def parse(json_obj: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(json_obj)

    parsed["description"] = normalize_string(parsed.get("description"))
    parsed["private"] = normalize_boolean(parsed.get("private"))
    parsed["gated"] = normalize_boolean(parsed.get("gated"))
    parsed["disabled"] = normalize_boolean(parsed.get("disabled"))

    tags = dedupe(parsed.get("tags", []))

    region_tokens = get_tag_with_prefix(tags, "region:")
    language_tokens = get_tag_with_prefix(tags, "language:") + get_tag_alone(tags, "language")
    license_tokens = get_tag_with_prefix(tags, "license:") + get_tag_alone(tags, "license")

    parsed["region_uris"] = build_uris(region_tokens, "region")
    parsed["language_uris"] = build_uris(language_tokens, "language")
    parsed["license_uris"] = build_uris(license_tokens, "license")

    source_dataset_values = get_tag_with_prefix(tags, "source_datasets:")
    source_dataset_hf, source_dataset_non_hf = split_hf_values(
        source_dataset_values, kind="dataset"
    )
    parsed["source_dataset_hf"] = source_dataset_hf
    parsed["source_dataset_non_hf_instances"] = [
        {
            "source_dataset_label": source_dataset_label,
            "source_dataset_hash16": hash16(source_dataset_label),
        }
        for source_dataset_label in source_dataset_non_hf
        if hash16(source_dataset_label)
    ]

    modalities = get_tag_with_prefix(tags, "modality:")

    # Thesaurus
    parsed["task_categories"] = canonicalize(get_tag_with_prefix(tags, "task_categories:") + get_canonical_tag_alone(tags, "task"), "task")
    parsed["task_ids"] = canonicalize(get_tag_with_prefix(tags, "task_ids:") + get_canonical_tag_alone(tags, "subtask"), "subtask")
    parsed["modalities"] = canonicalize(modalities + get_canonical_tag_alone(tags, "modality"), "modality")    
    parsed["types"] = canonicalize(modalities + get_canonical_tag_alone(tags, "type"), "type")
    parsed["libraries"] = canonicalize(get_tag_with_prefix(tags, "library:") + get_canonical_tag_alone(tags, "library"), "library")
    parsed["size_categories"] = canonicalize(get_tag_with_prefix(tags, "size_categories:") + get_canonical_tag_alone(tags, "size_category"), "size_category")
    parsed["formats"] = canonicalize(get_tag_with_prefix(tags, "format:") + get_canonical_tag_alone(tags, "format"), "format")
    parsed["multilinguality"] = canonicalize(get_tag_with_prefix(tags, "multilinguality:") + get_canonical_tag_alone(tags, "multilinguality"), "multilinguality")

    doi_ids = get_tag_with_prefix(tags, "doi:")
    arxiv_ids = get_tag_with_prefix(tags, "arxiv:")
    paperswithcode_id = normalize_string(parsed.get("paperswithcode_id"))
    parsed["paperid"] = doi_ids if doi_ids else (arxiv_ids if arxiv_ids else ([paperswithcode_id] if paperswithcode_id else None))
    parsed["doi"] = doi_ids
    parsed["paperurl"] = paper_url(
        [
            *[f"doi:{value}" for value in doi_ids],
            *[f"arxiv:{value}" for value in arxiv_ids],
            *([f"paperswithcode_id:{paperswithcode_id}"] if paperswithcode_id else []),
        ]
    )

    linguistic_methods = get_tag_with_prefix(tags, "language_creators:")
    annotation_methods = get_tag_with_prefix(tags, "annotations_creators:")
    parsed["language_creators"] = linguistic_methods
    parsed["annotations_creators"] = annotation_methods
    annotation_hash_payload = {
        "linguisticMethod": linguistic_methods,
        "annotationMethod": annotation_methods,
    }
    has_annotation_data = bool(linguistic_methods or annotation_methods)

    parsed["annotation_hash16"] = (
        hash16({json.dumps(annotation_hash_payload, sort_keys=True, ensure_ascii=False)})
        if has_annotation_data
        else None
    )
    parsed["dataset_hash16"] = hash16(parsed.get('id')) if parsed.get("id") else None
    parsed["distribution_hash16"] = hash16({json.dumps({"formats": parsed["formats"]}, sort_keys=True, ensure_ascii=False)} 
                                           if parsed["formats"] else None)
    parsed["creator_hash16"] = hash16(parsed.get('author')) if parsed.get("author") else None
    parsed["article_hash16"] = hash16({json.dumps({"paperswithcode_id": paperswithcode_id, "doi": sorted(doi_ids), "arxiv": sorted(arxiv_ids)}, sort_keys=True, ensure_ascii=False)} 
                                      if paperswithcode_id or doi_ids or arxiv_ids else None)

    parsed["tags"] = tags

    return parsed


def preprocess_file(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Expected JSON to be a list of documents (JSON array).")

    processed: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned = parse(item)
        processed.append(cleaned)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(processed, file, ensure_ascii=False, indent=2)

    print(f"File written: {output_path}")
    print(f"Documents processed: {len(processed)}")


if __name__ == "__main__":
    default_base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Unified parser for Hugging Face datasets: normalization, thesaurus enrichment, "
            "and generation of technical fields for XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_base_dir / "datasets.json",
        help="Source JSON file (default: datasets.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_base_dir / "datasets_parsed.json",
        help="Output JSON file (default: datasets_parsed.json)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write result directly to the input file",
    )
    args = parser.parse_args()

    source = args.input
    destination = args.input if args.in_place else args.output

    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")

    preprocess_file(source, destination)
