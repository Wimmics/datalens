import argparse
import json
from pathlib import Path
from typing import Any
from .parser_tools import (
    build_uris, canonicalize_modalities, dedupe, fallback_model_libraries, get_tag_values, hash16, infer_language_tokens,
    normalize_and_dedupe_tags, normalize_boolean, normalize_string, remove_consumed_tags, paper_url)

BASE_MODEL_RELATIONS = {
    "finetune": "finetuned",
    "finetuned": "finetuned",
    "fine-tune": "finetuned",
    "quantized": "quantized",
    "quantize": "quantized",
    "merge": "merged",
    "merged": "merged",
    "adapt": "adapter",
    "adapted": "adapter",
    "adapter": "adapter",
}

DERIVATION_TYPES = {
    "finetuned": "fineTune",
    "quantized": "quantize",
    "merged": "merge",
    "adapter": "adapt",
}

def author_from_hf_id(resource_id: str | None) -> str | None:
    normalized_id = normalize_string(resource_id)
    if not normalized_id or "/" not in normalized_id:
        return None
    owner, _, _ = normalized_id.partition("/")
    return normalize_string(owner)

def parse_base_model_tags(
    tags: list[str],
) -> list[dict[str, Any]]:
    prefix = "base_model:"
    grouped_ids: dict[str, list[str]] = {key: [] for key in DERIVATION_TYPES}

    for tag in tags:
        if not tag.lower().startswith(prefix):
            continue
        payload = tag[len(prefix) :]
        if not payload:
            continue

        left, sep, right = payload.partition(":")
        group = BASE_MODEL_RELATIONS.get(left.lower()) if sep else None
        if group and right:
            grouped_ids[group].append(right)

    grouped_ids = {key: dedupe(values) for key, values in grouped_ids.items()}

    source_models: list[dict[str, Any]] = []
    seen_source_models: set[str] = set()

    def add_derivation(transformation_type: str, source_hashes: list[str], seed: str) -> None:
        if not source_hashes or not seed:
            return
        derivation_hash = hash16(f"{transformation_type}:{seed}")
        if not derivation_hash or derivation_hash in seen_source_models:
            return
        seen_source_models.add(derivation_hash)
        source_models.append(
            {
                "source_model_hash16": source_hashes,
                "transformation_type": transformation_type,
                "derivation_hash16": derivation_hash,
            }
        )

    merge_ids = grouped_ids["merged"]
    merge_hashes = [hash16(source_model_id) for source_model_id in merge_ids]
    merge_hashes = [value for value in merge_hashes if value]
    add_derivation(DERIVATION_TYPES["merged"], merge_hashes, "|".join(sorted(merge_ids)))

    for group_key in ("finetuned", "quantized", "adapter"):
        transformation_type = DERIVATION_TYPES[group_key]
        for source_model_id in grouped_ids[group_key]:
            source_hash = hash16(source_model_id)
            if source_hash:
                add_derivation(transformation_type, [source_hash], source_model_id)

    return source_models


def parse(json_obj: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parsed = dict(json_obj)

    parsed["author"] = author_from_hf_id(parsed["id"])
    parsed["private"] = normalize_boolean(parsed.get("private"))
    parsed["gated"] = normalize_boolean(parsed.get("gated"))
    parsed["disabled"] = normalize_boolean(parsed.get("disabled"))

    tags, removed_count = normalize_and_dedupe_tags(parsed.get("tags", []))

    region_tokens = dedupe(get_tag_values(tags, "region:"))
    explicit_language_values = get_tag_values(tags, "language:")
    language_tokens = infer_language_tokens(tags, explicit_language_values)
    license_tokens = dedupe(get_tag_values(tags, "license:"))

    parsed["language_uris"] = build_uris(language_tokens, "language")
    parsed["region_uris"] = build_uris(region_tokens, "region")
    parsed["license_uris"] = build_uris(license_tokens, "license")

    parsed["task_categories"] = normalize_string(parsed.get("pipeline_tag"))
    parsed["modalities"] = canonicalize_modalities(dedupe(get_tag_values(tags, "modality:")))
    (parsed["thesaurus_libraries"],parsed["fallback_instances"]) = fallback_model_libraries([parsed.get("library_name")] + dedupe(get_tag_values(tags, "library:")))
    parsed["formats"] = dedupe(get_tag_values(tags, "format:"))

    doi_ids = dedupe(get_tag_values(tags, "doi:"))
    arxiv_ids = dedupe(get_tag_values(tags, "arxiv:"))
    parsed["paperid"] = doi_ids if doi_ids else (arxiv_ids if arxiv_ids else None)    
    parsed["doi"] = dedupe(get_tag_values(tags, "doi:"))
    parsed["paperurl"] = paper_url(
        [
            *[f"doi:{value}" for value in doi_ids],
            *[f"arxiv:{value}" for value in arxiv_ids],
        ]
    )

    dataset_ids = dedupe(get_tag_values(tags, "dataset:"))
    parsed["datasets_hash16"] = [hash16(dataset_id) for dataset_id in dataset_ids]
    source_models = parse_base_model_tags(tags)
    parsed["source_models"] = source_models

    parsed["article_hash16"] = hash16({json.dumps({"doi": sorted(doi_ids), "arxiv": sorted(arxiv_ids)}, sort_keys=True, ensure_ascii=False)} 
                                      if doi_ids or arxiv_ids else None)
    parsed["model_hash16"] = hash16(parsed.get("id")) if parsed.get("id") else None
    parsed["distribution_hash16"] = hash16({json.dumps({"formats": parsed["formats"]}, sort_keys=True, ensure_ascii=False)} 
                                           if parsed["formats"] else None)
    parsed["creator_hash16"] = hash16(parsed.get("author")) if parsed.get("author") else None

    paperid_values = parsed["paperid"] or []
    tags, consumed_removed_count = remove_consumed_tags(
        tags,
        exact_tags=dedupe(language_tokens + parsed["formats"] + parsed["thesaurus_libraries"] + [parsed["task_categories"]] + paperid_values + dataset_ids),
        prefixes=[
            "region:",
            "language:",
            "format:",
            "license:",
            "modality:",
            "library:",
            "doi:",
            "arxiv:",
            "dataset:",
            "base_model:",
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
            "Parser unifie pour les modeles Hugging Face: normalisation, enrichissement "
            "et generation des champs techniques pour XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_base_dir / "models.json",
        help="Fichier JSON source (par defaut: models.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_base_dir / "models_parsed.json",
        help="Fichier JSON de sortie (par defaut: models_parsed.json)",
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
