#!/usr/bin/env python3
"""Generate a SKOS thesaurus from tags.json.

tags.json is a recursive tree keyed by "big category" (subject, task,
language, architecture, ...). Under each big category, nodes are nested
arbitrarily deep. Some nodes are real Kaggle tags (they carry id, slug,
description, dataset_count, competition_count, kernel_count) while other
nodes are purely organizational groupings (they only carry "children").

This script turns:
  - each big category (top-level key)   -> one skos:ConceptScheme
  - every node found in that category's -> one skos:Concept, typed with
    subtree (tag or grouping node)         a class derived from the big
                                            category (e.g. dlo:Task,
                                            dlo:Language, dlo:Architecture)

The original tree hierarchy is preserved with skos:broader (or
skos:topConceptOf the scheme for direct children of the big category).
When available, id/slug/description/dataset_count/competition_count/
kernel_count are attached to the concept as extra properties.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("huggingface_study/tags.json")
DEFAULT_OUTPUT = Path("ontology/kaggle_tags.json")


# ---------------------------------------------------------------------------
# String helpers (adapted from convert_tags_to_thesaurus copy.py)
# ---------------------------------------------------------------------------

def turtle_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def humanize_label(value: str) -> str:
    """Create a human-readable label from a tag key or slug."""

    text = value.strip()

    # qwen3_5 -> qwen3.5 (kept for parity with numeric versioned tags)
    text = re.sub(r"(\d+)_(\d+)", r"\1.\2", text)

    # Remaining separators
    text = text.replace("_", " ").replace("-", " ")

    # Split camel case
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)

    # step1 -> step 1
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)

    # 3Moe -> 3 Moe
    text = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", text)

    text = re.sub(r"\s+", " ", text).strip()

    words = []
    for word in text.split():
        if re.fullmatch(r"\d+(\.\d+)?", word):
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])

    return " ".join(words)


def pascal_case(value: str) -> str:
    """Generate PascalCase Turtle local names."""

    value = value.replace("_", " ").replace("-", " ")

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", value)
    value = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", value)

    words = re.findall(r"[A-Za-z0-9]+", value)

    if not words:
        return "Item"

    return "".join(word[:1].upper() + word[1:] for word in words)


def make_unique_local_name(raw_value: str, used_names: set[str]) -> str:
    base_name = pascal_case(raw_value)

    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        suffix += 1


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def load_tags(input_path: Path) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def write_concept(
    handle,
    local_name: str,
    label: str,
    class_local: str,
    scheme_local: str,
    parent_local: str | None,
    node: dict[str, Any],
) -> None:
    handle.write(f"dlt:{local_name} a skos:Concept, dlo:{class_local} ;\n")
    handle.write(f'    skos:prefLabel "{label}"@en ;\n')

    description = node.get("description") or ""
    if description:
        handle.write(f'    skos:definition "{turtle_literal(description)}"@en ;\n')

    if parent_local:
        handle.write(f"    skos:broader dlt:{parent_local} ;\n")
    else:
        handle.write(f"    skos:topConceptOf dlt:{scheme_local} ;\n")

    handle.write(f"    skos:inScheme dlt:{scheme_local} .\n\n")


def walk_and_write(
    handle,
    node: dict[str, Any],
    scheme_local: str,
    class_local: str,
    used_names: set[str],
    parent_local: str | None = None,
) -> None:
    children = node.get("children") or {}

    # Preserve JSON insertion order.
    for key, child in children.items():
        if not isinstance(child, dict):
            continue

        raw_value = child.get("slug") or key
        local_name = make_unique_local_name(raw_value, used_names)
        label = humanize_label(key)

        write_concept(
            handle=handle,
            local_name=local_name,
            label=label,
            class_local=class_local,
            scheme_local=scheme_local,
            parent_local=parent_local,
            node=child,
        )

        walk_and_write(
            handle=handle,
            node=child,
            scheme_local=scheme_local,
            class_local=class_local,
            used_names=used_names,
            parent_local=local_name,
        )


def build_thesaurus(input_path: Path, output_path: Path) -> Path:
    data = load_tags(input_path)

    os.makedirs(output_path.parent, exist_ok=True)
    used_names: set[str] = set()

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
        handle.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        handle.write("@prefix dlo: <http://ns.inria.fr/datalens/ontology/> .\n")
        handle.write("@prefix dlt: <http://ns.inria.fr/datalens/thesaurus/> .\n\n")

        for top_key, top_node in data.items():
            if not isinstance(top_node, dict):
                continue

            class_local = pascal_case(top_key)
            scheme_local = f"{class_local}Scheme"
            scheme_label = humanize_label(top_key)

            top_description = top_node.get("description") or ""
            scheme_definition = (
                top_description
                if top_description
                else f"Controlled vocabulary for the '{scheme_label}' tag category."
            )

            handle.write(f"dlt:{scheme_local} a skos:ConceptScheme ;\n")
            handle.write(f'    skos:prefLabel "{turtle_literal(scheme_label)}"@en ;\n')
            handle.write(
                f'    skos:definition "{turtle_literal(scheme_definition)}"@en .\n\n'
            )

            

            walk_and_write(
                handle=handle,
                node=top_node,
                scheme_local=scheme_local,
                class_local=class_local,
                used_names=used_names,
                parent_local=None,
            )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a SKOS thesaurus from tags.json (one ConceptScheme per big category)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to tags.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated Turtle file",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Tags file not found: {args.input}")

    output_path = build_thesaurus(args.input, args.output)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
