import argparse
import json
from pathlib import Path
from typing import Any

from .canonical_thesaurus import canonicalize
from .parser_tools import (
    normalize_string,
    build_uris,
    hash16,
)


def split_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [
        tag.strip().lower()
        for tag in tags.split(",")
        if tag.strip()
    ]


def parse(json_obj: dict[str, Any]) -> dict[str, Any]:

    parsed = dict(json_obj)

    parsed["id"] = parsed["Version_Slug"]
    parsed["description"] = normalize_string(parsed["Version_Description"])
    parsed["created_at"] = parsed["Version_CreationDate"]
    parsed["last_modified"] = parsed["LastActivityDate"]
    parsed["downloads"] = parsed["TotalDownloads"]
    parsed["likes"] = parsed["TotalVotes"]
    parsed["author_user"] = normalize_string(parsed["Owner_UserName"])
    parsed["author_organisation"] = normalize_string(parsed["Owner_Organisation"])

    parsed["tags"] = split_tags(parsed["Tags"])

    parsed["modalities"] = canonicalize(parsed["tags"], "modality")
    parsed["task_categories"] = canonicalize(parsed["tags"], "task")
    parsed["task_ids"] = canonicalize(parsed["tags"], "subtask")
    parsed["libraries"] = canonicalize(parsed["tags"], "dataset_library")
    parsed["formats"] = canonicalize(parsed["tags"], "format")
    parsed["size_categories"] = canonicalize(parsed["tags"], "size")

    parsed["license_uris"] = build_uris(
        parsed["Version_LicenseName"], "license"
    )

    parsed["dataset_hash16"] = hash16(parsed["Id"])
    parsed["creator_hash16"] = hash16(parsed["author"])

    parsed["distribution_hash16"] = hash16({
        "compressed": parsed["Version_TotalCompressedBytes"],
        "uncompressed": parsed["Version_TotalUncompressedBytes"],
        "formats": parsed["formats"],
    })

    return parsed


def preprocess_file(input_path: Path, output_path: Path) -> None:

    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Expected JSON array.")

    processed = []

    for item in data:
        if isinstance(item, dict):
            processed.append(parse(item))

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            processed,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"File written: {output_path}")
    print(f"Documents processed: {len(processed)}")


if __name__ == "__main__":

    base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Parser Kaggle datasets"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=base_dir / "datasets.json",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=base_dir / "datasets_parsed.json",
    )

    parser.add_argument(
        "--in-place",
        action="store_true",
    )

    args = parser.parse_args()

    source = args.input
    destination = source if args.in_place else args.output

    if not source.exists():
        raise FileNotFoundError(source)

    preprocess_file(source, destination)