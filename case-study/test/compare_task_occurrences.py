from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


def find_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "src").exists() and (candidate / "case-study").exists():
            return candidate
    return current


ROOT = find_root(Path.cwd())
DEFAULT_OLD = ROOT / "case-study" / "data" / "input" / "datasets_new.json"
DEFAULT_NEW = ROOT / "case-study" / "data" / "input" / "datasets_new_new.json"


def ensure_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize(value: str) -> str:
    return str(value).strip().lower()


def values_from_tags(tags: object, prefix: str) -> list[str]:
    if not isinstance(tags, list):
        return []

    out: list[str] = []
    marker = f"{prefix}:"
    for tag in tags:
        if isinstance(tag, str) and tag.startswith(marker):
            tail = normalize(tag[len(marker) :])
            if tail:
                out.append(tail)
    return out


def extract_field_values(row: dict, field: str) -> list[str]:
    # Priority to explicit field; fallback to tags when missing.
    explicit = row.get(field)
    if explicit is not None:
        return [normalize(v) for v in ensure_list(explicit) if normalize(v)]

    tags = row.get("tags")
    return values_from_tags(tags, field)


def counters_for_file(path: Path) -> tuple[Counter, Counter, int]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected top-level JSON list in {path}")

    task_ids_counter: Counter = Counter()
    task_categories_counter: Counter = Counter()
    row_count = 0

    for row in data:
        if not isinstance(row, dict):
            continue
        row_count += 1

        task_ids = extract_field_values(row, "task_ids")
        task_categories = extract_field_values(row, "task_categories")

        task_ids_counter.update(task_ids)
        task_categories_counter.update(task_categories)

    return task_ids_counter, task_categories_counter, row_count


def positive_deltas(old_counter: Counter, new_counter: Counter) -> list[tuple[str, int, int, int]]:
    rows: list[tuple[str, int, int, int]] = []
    keys = set(old_counter) | set(new_counter)

    for key in keys:
        old_v = old_counter.get(key, 0)
        new_v = new_counter.get(key, 0)
        delta = new_v - old_v
        if delta > 0:
            rows.append((key, old_v, new_v, delta))

    rows.sort(key=lambda x: (x[3], x[2], x[0]), reverse=True)
    return rows


def print_section(title: str, rows: Iterable[tuple[str, int, int, int]], limit: int) -> None:
    rows = list(rows)
    print(f"\n=== {title} ===")
    print(f"new_or_increased_count: {len(rows)}")

    if not rows:
        print("No new or increased occurrences.")
        return

    print("value | old | new | delta")
    for value, old_v, new_v, delta in rows[:limit]:
        print(f"{value} | {old_v} | {new_v} | +{delta}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare datasets_new.json and datasets_new_new.json for task_ids/task_categories "
            "and report new or increased occurrences."
        )
    )
    parser.add_argument("--old", type=Path, default=DEFAULT_OLD, help=f"Old JSON file (default: {DEFAULT_OLD})")
    parser.add_argument("--new", type=Path, default=DEFAULT_NEW, help=f"New JSON file (default: {DEFAULT_NEW})")
    parser.add_argument("--limit", type=int, default=30, help="Max rows to print per section")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    old_path: Path = args.old
    new_path: Path = args.new

    missing = [p for p in [old_path, new_path] if not p.exists()]
    if missing:
        print("Missing input file(s):")
        for p in missing:
            print(f"- {p}")
        return 1

    try:
        old_task_ids, old_task_categories, old_rows = counters_for_file(old_path)
        new_task_ids, new_task_categories, new_rows = counters_for_file(new_path)
    except Exception as exc:
        print(f"Error: {exc}")
        return 2

    print("Comparison summary")
    print(f"old_file: {old_path}")
    print(f"new_file: {new_path}")
    print(f"old_rows: {old_rows}")
    print(f"new_rows: {new_rows}")

    ids_pos = positive_deltas(old_task_ids, new_task_ids)
    categories_pos = positive_deltas(old_task_categories, new_task_categories)

    print_section("task_ids (new or increased)", ids_pos, args.limit)
    print_section("task_categories (new or increased)", categories_pos, args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
