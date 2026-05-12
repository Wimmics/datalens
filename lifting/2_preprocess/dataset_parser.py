import argparse
import json
from typing import Any
from pathlib import Path
from .canonical_thesaurus import canonicalize, get_tag_alone
from .parser_tools import (
    build_uris, dedupe, get_tag_with_prefix, hash16, infer_language_tokens,
    normalize_and_dedupe_tags, normalize_boolean, normalize_string, remove_consumed_tags, paper_url)


def parse(json_obj: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parsed = dict(json_obj)

    parsed["description"] = normalize_string(parsed.get("description"))
    parsed["private"] = normalize_boolean(parsed.get("private"))
    parsed["gated"] = normalize_boolean(parsed.get("gated"))
    parsed["disabled"] = normalize_boolean(parsed.get("disabled"))

    tags, removed_count = normalize_and_dedupe_tags(parsed.get("tags", []))

    region_tokens = get_tag_with_prefix(tags, "region:")
    explicit_language_values = get_tag_with_prefix(tags, "language:")
    language_tokens = infer_language_tokens(tags, explicit_language_values)
    license_tokens = get_tag_with_prefix(tags, "license:")

    parsed["language_uris"] = build_uris(language_tokens, "language")
    parsed["region_uris"] = build_uris(region_tokens, "region")
    parsed["license_uris"] = build_uris(license_tokens, "license")

    # Thesaurus
    parsed["task_categories"] = canonicalize(get_tag_with_prefix(tags, "task_categories:") + get_tag_alone(tags, "task"), "task")
    parsed["task_ids"] = canonicalize(get_tag_with_prefix(tags, "task_ids:") + get_tag_alone(tags, "subtask"), "subtask")
    parsed["modalities"] = canonicalize(get_tag_with_prefix(tags, "modality:") + get_tag_alone(tags, "modality"), "modality")
    parsed["libraries"] = canonicalize(get_tag_with_prefix(tags, "library:") + get_tag_alone(tags, "dataset_library"), "dataset_library")
    parsed["size_categories"] = canonicalize(get_tag_with_prefix(tags, "size_categories:") + get_tag_alone(tags, "size_category"), "size_category")
    parsed["formats"] = canonicalize(get_tag_with_prefix(tags, "format:") + get_tag_alone(tags, "format"), "format")

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

    paperid_values = parsed["paperid"] or []
    tags, consumed_removed_count = remove_consumed_tags(
        tags,
        exact_tags=dedupe(
            language_tokens
            + license_tokens
            + parsed["formats"]
            + parsed["task_categories"]
            + parsed["task_ids"]
            + parsed["modalities"]
            + parsed["libraries"]
            + parsed["size_categories"]
            + paperid_values
            + linguistic_methods
            + annotation_methods
        ),
        prefixes=[
            "region:",
            "language:",
            "format:",
            "license:",
            "task_categories:",
            "task_ids:",
            "modality:",
            "library:",
            "size_categories:",
            "doi:",
            "arxiv:",
            "language_creators:",
            "annotations_creators:",
        ],
    )
    parsed["tags"] = tags

    return parsed, removed_count + consumed_removed_count


def preprocess_file(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Le JSON attendu est une liste de documents (tableau JSON).")

    processed: list[dict[str, Any]] = []
    total_removed = 0
    docs_with_removed = 0

    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned, removed = parse(item)
        processed.append(cleaned)
        total_removed += removed
        if removed > 0:
            docs_with_removed += 1

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(processed, file, ensure_ascii=False, indent=2)

    print(f"Fichier ecrit: {output_path}")
    print(f"Documents traites: {len(processed)}")
    print(f"Documents avec doublons supprimes: {docs_with_removed}")
    print(f"Total tags dupliques supprimes: {total_removed}")


if __name__ == "__main__":
    default_base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Parser unifie pour les datasets Hugging Face: normalisation, enrichissement "
            "thesaurus et generation des champs techniques pour XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_base_dir / "datasets.json",
        help="Fichier JSON source (par defaut: datasets.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_base_dir / "datasets_parsed.json",
        help="Fichier JSON de sortie (par defaut: datasets_parsed.json)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Ecrit le resultat directement dans le fichier --input",
    )
    args = parser.parse_args()

    source = args.input
    destination = args.input if args.in_place else args.output

    if not source.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source}")

    preprocess_file(source, destination)
