"""
Prétraitement de datasets.json pour limiter les triples dupliqués générés par des
variantes de formatage dans les tags (casse, espaces, doublons exacts, etc.).

Ce script :
- normalise les tags (trim, espaces autour de ":", minuscule) ;
- supprime les doublons de tags en conservant l'ordre ;
- extrait des champs structurés depuis les tags (task_ids, task_categories,
  modalities, languages, size_categories) ;
- pré-calcule des identifiants techniques en SHA-256 tronqué (16 caractères)
    pour dataset/distribution/creator/article ;
- normalise certains champs textuels utiles (id, author, paperswithcode_id) ;
- convertit private/gated/disabled en booléens robustes.

Entrée par défaut  : datasets.json
Sortie par défaut  : datasets_preprocessed.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SPACE_AROUND_COLON = re.compile(r"\s*:\s*")
MULTI_SPACE = re.compile(r"\s+")
SIZE_CATEGORY_UNITS = re.compile(r"(?<=\d)([kmbt])\b")


def normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = MULTI_SPACE.sub(" ", value).strip()
    return normalized or None


def normalize_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n", "", "none", "null"}:
            return False
    return False


def normalize_tag(tag: Any) -> str | None:
    text = normalize_string(tag)
    if not text:
        return None

    text = SPACE_AROUND_COLON.sub(":", text)
    text = text.lower()
    return text


def deduplicate_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def short_sha256(value: Any, length: int = 16) -> str | None:
    normalized = normalize_string(value)
    if not normalized:
        return None
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:length]


def collect_tag_values(tags: list[str], prefix: str) -> list[str]:
    values: list[str] = []
    for tag in tags:
        if not tag.startswith(prefix):
            continue
        value = tag.split(":", 1)[1].strip()
        if value:
            values.append(value)
    return deduplicate_preserve_order(values)


MODALITY_CANONICAL = {
    "text": "Text",
    "tabular": "Tabular",
    "image": "Image",
    "audio": "Audio",
    "video": "Video",
    "timeseries": "TimeSeries",
    "time_series": "TimeSeries",
    "time-series": "TimeSeries",
}


def canonicalize_modality(value: str) -> str:
    return MODALITY_CANONICAL.get(value, value.replace("_", "-").title().replace("-", ""))


def normalize_size_category(value: str) -> str:
    return SIZE_CATEGORY_UNITS.sub(lambda match: match.group(1).upper(), value)


def preprocess_document(document: dict[str, Any]) -> tuple[dict[str, Any], int]:
    cleaned = dict(document)

    for field in ("id", "author", "paperswithcode_id"):
        if field in cleaned:
            cleaned[field] = normalize_string(cleaned.get(field))

    for field in ("private", "gated", "disabled"):
        if field in cleaned:
            cleaned[field] = normalize_boolean(cleaned.get(field))

    raw_tags = cleaned.get("tags", [])
    if not isinstance(raw_tags, list):
        raw_tags = []

    normalized_tags = [tag for tag in (normalize_tag(item) for item in raw_tags) if tag]
    deduped_tags = deduplicate_preserve_order(normalized_tags)

    adjusted_tags: list[str] = []
    for tag in deduped_tags:
        if tag.startswith("size_categories:"):
            prefix, size_value = tag.split(":", 1)
            adjusted_tags.append(f"{prefix}:{normalize_size_category(size_value)}")
        else:
            adjusted_tags.append(tag)

    removed_count = len(normalized_tags) - len(deduped_tags)
    cleaned["tags"] = adjusted_tags
    cleaned["tags_repr"] = str(adjusted_tags) if adjusted_tags else None

    cleaned["task_ids"] = collect_tag_values(adjusted_tags, "task_ids:")
    cleaned["task_categories"] = collect_tag_values(adjusted_tags, "task_categories:")
    cleaned["modalities"] = collect_tag_values(adjusted_tags, "modality:")
    cleaned["modalities_pref"] = [canonicalize_modality(modality) for modality in cleaned["modalities"]]
    cleaned["languages"] = collect_tag_values(adjusted_tags, "language:")
    cleaned["size_categories"] = [normalize_size_category(value) for value in collect_tag_values(adjusted_tags, "size_categories:")]
    cleaned["size_categories_repr"] = str(cleaned["size_categories"]) if cleaned["size_categories"] else None
    cleaned["task_id_first"] = cleaned["task_ids"][0] if cleaned["task_ids"] else None
    cleaned["task_category_first"] = cleaned["task_categories"][0] if cleaned["task_categories"] else None
    cleaned["modality_first"] = cleaned["modalities_pref"][0] if cleaned["modalities_pref"] else None
    cleaned["language_first"] = cleaned["languages"][0] if cleaned["languages"] else None

    usage_parts = []
    if cleaned["task_ids"]:
        usage_parts.append("task_ids:" + "_".join(cleaned["task_ids"]))
    if cleaned["task_categories"]:
        usage_parts.append("task_categories:" + "_".join(cleaned["task_categories"]))
    usage_seed = "|".join(usage_parts) if usage_parts else None

    cleaned["dataset_hash16"] = short_sha256(cleaned.get("id"))
    cleaned["distribution_hash16"] = short_sha256(f"distribution:{cleaned.get('id')}") if cleaned.get("id") else None
    cleaned["creator_hash16"] = short_sha256(f"creator:{cleaned.get('author')}") if cleaned.get("author") else None
    cleaned["article_hash16"] = short_sha256(f"pwc:{cleaned.get('paperswithcode_id')}") if cleaned.get("paperswithcode_id") else None
    cleaned["usage_hash16"] = short_sha256(usage_seed) if usage_seed else None

    return cleaned, removed_count


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
        cleaned, removed = preprocess_document(item)
        processed.append(cleaned)
        total_removed += removed
        if removed > 0:
            docs_with_removed += 1

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(processed, file, ensure_ascii=False, indent=2)

    exploded_modalities: list[dict[str, Any]] = []
    exploded_subjects: list[dict[str, Any]] = []
    exploded_languages: list[dict[str, Any]] = []
    exploded_task_categories: list[dict[str, Any]] = []
    exploded_task_ids: list[dict[str, Any]] = []
    exploded_usage_tasks: list[dict[str, Any]] = []
    exploded_usage_task_categories: list[dict[str, Any]] = []

    for item in processed:
        dataset_hash = item.get("dataset_hash16")
        if not dataset_hash:
            continue

        for modality in item.get("modalities_pref", []):
            exploded_modalities.append(
                {
                    "dataset_hash16": dataset_hash,
                    "modality": modality,
                }
            )

        for tag in item.get("tags", []):
            exploded_subjects.append(
                {
                    "dataset_hash16": dataset_hash,
                    "subject": tag,
                }
            )

        for language in item.get("languages", []):
            exploded_languages.append(
                {
                    "dataset_hash16": dataset_hash,
                    "language": language,
                }
            )

        for task_category in item.get("task_categories", []):
            exploded_task_categories.append(
                {
                    "dataset_hash16": dataset_hash,
                    "task_category": task_category,
                }
            )

        for task_id in item.get("task_ids", []):
            exploded_task_ids.append(
                {
                    "dataset_hash16": dataset_hash,
                    "task_id": task_id,
                }
            )

        usage_hash = item.get("usage_hash16")
        if usage_hash:
            for task_id in item.get("task_ids", []):
                exploded_usage_tasks.append(
                    {
                        "usage_hash16": usage_hash,
                        "task_id": task_id,
                    }
                )
            for task_category in item.get("task_categories", []):
                exploded_usage_task_categories.append(
                    {
                        "usage_hash16": usage_hash,
                        "task_category": task_category,
                    }
                )

    exploded_outputs = {
        "datasets_modalities.json": exploded_modalities,
        "datasets_subjects.json": exploded_subjects,
        "datasets_languages.json": exploded_languages,
        "datasets_task_categories.json": exploded_task_categories,
        "datasets_task_ids.json": exploded_task_ids,
        "datasets_usage_tasks.json": exploded_usage_tasks,
        "datasets_usage_task_categories.json": exploded_usage_task_categories,
    }

    for filename, payload in exploded_outputs.items():
        out_file = output_path.parent / filename
        with out_file.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"Fichier écrit: {output_path}")
    print(f"Documents traités: {len(processed)}")
    print(f"Documents avec doublons supprimés: {docs_with_removed}")
    print(f"Total tags dupliqués supprimés: {total_removed}")
    for filename, payload in exploded_outputs.items():
        print(f"Fichier écrit: {output_path.parent / filename} ({len(payload)} enregistrements)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prétraite datasets.json (normalisation + déduplication) pour limiter "
            "les triples répétés côté XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "datasets.json",
        help="Fichier JSON source (par défaut: datasets.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "datasets_preprocessed.json",
        help="Fichier JSON de sortie (par défaut: datasets_preprocessed.json)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Écrit le résultat directement dans le fichier --input",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    source = args.input
    destination = args.input if args.in_place else args.output

    if not source.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source}")

    preprocess_file(source, destination)