from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
    else:
        text = str(value).strip()
    return text or None


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return normalize_string(value) is None

    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0

    try:
        return value != value
    except Exception:
        return False


def summarize_field_emptiness(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, int | str]]:
    records = list(rows)
    field_names = sorted({field for row in records for field in row.keys()})
    summary: list[dict[str, int | str]] = []

    for field in field_names:
        empty_count = 0
        full_count = 0

        for row in records:
            if _is_empty_value(row.get(field)):
                empty_count += 1
            else:
                full_count += 1

        summary.append(
            {
                "field": field,
                "empty_count": empty_count,
                "full_count": full_count,
                "total_count": len(records),
            }
        )

    return summary


def load_records(input_path: Path) -> list[dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        records = [row for row in data if isinstance(row, dict)]
        if len(records) != len(data):
            raise ValueError("Le JSON d'entrée doit contenir uniquement des objets dans la liste.")
        return records

    if isinstance(data, dict):
        return [data]

    raise ValueError("Le JSON d'entrée doit être une liste d'objets ou un objet JSON unique.")


def build_output(records: list[dict[str, Any]], source: Path) -> dict[str, Any]:
    return {
        "source_file": str(source),
        "record_count": len(records),
        "fields": summarize_field_emptiness(records),
    }


def main() -> None:
    args = {"input_json": Path("kaggle_study\\all_models_variations.json"), "output_json": Path("kaggle_study\\variations_empty.json")}


    records = load_records(args["input_json"])
    output = build_output(records, args["input_json"])

    args["output_json"].parent.mkdir(parents=True, exist_ok=True)
    with args["output_json"].open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()