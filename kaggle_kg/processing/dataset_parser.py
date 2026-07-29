import argparse
import json
from pathlib import Path
from typing import Any
from .canonical_thesaurus import canonicalize, get_canonical_tag_alone
from .parser_tools import (
    build_uris, dedupe, get_tag_alone, get_tag_with_prefix, hash16, normalize_string,
)


def parse(json_obj: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(json_obj)

    slug = normalize_string(parsed.get("Latest_Slug")) or ""

    if parsed.get("Owner_UserName"):
        parsed["authorUser"] = normalize_string(parsed.get("Owner_UserName")) or ""
        parsed["authorOrganization"] = normalize_string(parsed.get("Owner_Organizations")) or ""
        parsed["id"] = normalize_string(parsed.get("authorUser") + "/" + slug)
    else:
        parsed["authorOrganization"] = normalize_string(parsed.get("Organization_Name")) or ""
        parsed["id"] = normalize_string(parsed.get("authorOrganization") + "/" + slug)

    subtitle = normalize_string(parsed.get("Latest_Subtitle")) or ""
    description = normalize_string(parsed.get("Latest_Description")) or ""
    parsed["description"] = normalize_string(subtitle + "\n\n" + description)
    parsed["created_at"] = normalize_string(parsed.get("CreationDate"))
    parsed["last_modified"] = normalize_string(parsed.get("LastActivityDate"))
    parsed["downloads"] = normalize_string(parsed.get("TotalDownloads"))
    parsed["likes"] = normalize_string(parsed.get("TotalVotes"))
    parsed["views"] = normalize_string(parsed.get("TotalViews"))
    parsed["kernels"] = normalize_string(parsed.get("TotalKernels"))
    parsed["size_compressed"] = normalize_string(parsed.get("Latest_TotalCompressedBytes"))
    parsed["size_uncompressed"] = normalize_string(parsed.get("Latest_TotalUncompressedBytes"))

    tags_raw = parsed.get("Tags", "") or ""
    tags = dedupe([tag.strip() for tag in tags_raw.split(",") if tag.strip()])

    region_tokens = get_tag_with_prefix(tags, "region:")
    language_tokens = get_tag_with_prefix(tags, "language:") + get_tag_alone(tags, "language")
    license_tokens = normalize_string(parsed.get("Latest_LicenseName")) or ""

    parsed["region_uris"] = build_uris(region_tokens, "region")
    parsed["language_uris"] = build_uris(language_tokens, "language")
    parsed["license_uris"] = build_uris(license_tokens, "license")

    # Thesaurus
    parsed["model_families"] = canonicalize(get_canonical_tag_alone(tags, "architecture"), "architecture")
    parsed["modalities"] = canonicalize(get_canonical_tag_alone(tags, "kaggle_modality"), "kaggle_modality")
    parsed["audiences"] = canonicalize(get_canonical_tag_alone(tags, "audience"), "audience")
    parsed["libraries"] = canonicalize(get_canonical_tag_alone(tags, "library"), "library")
    parsed["subjects"] = canonicalize(get_canonical_tag_alone(tags, "subject"), "subject")
    parsed["tasks"] = canonicalize(get_canonical_tag_alone(tags, "kaggle_task"), "kaggle_task")

    parsed["dataset_hash16"] = hash16(parsed.get('id')) if parsed.get("id") else None
    parsed["creator_user_hash16"] = hash16(parsed.get('authorUser')) if parsed.get("authorUser") else None
    parsed["creator_organization_hash16"] = hash16(parsed.get('authorOrganization')) if parsed.get("authorOrganization") else None

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