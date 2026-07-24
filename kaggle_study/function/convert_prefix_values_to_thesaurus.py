#!/usr/bin/env python3
"""Generate a SKOS thesaurus from all_prefix_values_models.txt / _datasets.txt.

Each input file is a flat report with sections such as:

    multilinguality
    ===============
    monolingual : 54905
    multilingual : 5841
    ...

    diffusers
    =========
    Aucune occurrence

A section with no entries is written as "Aucune occurrence" and is skipped.

This script merges the two reports (models and datasets) and turns:
  - each section (prefix name, e.g. "multilinguality", "diffusers", "loss")
    -> one skos:ConceptScheme
  - every value listed under a section
    -> one skos:Concept, typed with a class derived from the section
       (e.g. dlo:Multilinguality, dlo:Diffusers, dlo:Loss)

The occurrence counts from each source file are kept as separate
properties (dlo:modelCount / dlo:datasetCount) on the concept, since the
same value can appear in both files with different counts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


DEFAULT_MODELS_INPUT = Path("huggingface_study/all_prefix_values_models.txt")
DEFAULT_DATASETS_INPUT = Path("huggingface_study/all_prefix_values_datasets.txt")
DEFAULT_OUTPUT = Path("ontology/prefix_values_thesaurus.ttl")

NO_OCCURRENCE_MARKER = "Aucune occurrence"


# ---------------------------------------------------------------------------
# String helpers (kept consistent with the other conversion scripts)
# ---------------------------------------------------------------------------

def turtle_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def humanize_label(value: str) -> str:
    """Create a human-readable label from a raw prefix value."""

    text = value.strip()

    text = re.sub(r"(\d+)_(\d+)", r"\1.\2", text)
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)
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
# Parsing
# ---------------------------------------------------------------------------

def parse_prefix_file(path: Path) -> "dict[str, list[tuple[str, int]]]":
    """Parse a report file into {section_name: [(value, count), ...]}."""

    sections: dict[str, list[tuple[str, int]]] = {}

    if not path or not path.exists():
        return sections

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = [line.rstrip("\r\n") for line in handle]

    i = 0
    current_section: str | None = None
    while i < len(lines):
        line = lines[i]

        # A section header is a non-empty line immediately followed by a
        # line made only of "=" characters.
        if (
            line.strip()
            and i + 1 < len(lines)
            and re.fullmatch(r"=+", lines[i + 1].strip())
        ):
            current_section = line.strip()
            sections.setdefault(current_section, [])
            i += 2
            continue

        stripped = line.strip()
        if not stripped or current_section is None:
            i += 1
            continue

        if stripped == NO_OCCURRENCE_MARKER:
            i += 1
            continue

        if " : " in stripped:
            value, count_text = stripped.rsplit(" : ", 1)
            value = value.strip()
            try:
                count = int(count_text.strip())
            except ValueError:
                i += 1
                continue
            if value:
                sections[current_section].append((value, count))

        i += 1

    return sections


def merge_sections(
    models_sections: "dict[str, list[tuple[str, int]]]",
    datasets_sections: "dict[str, list[tuple[str, int]]]",
) -> "dict[str, dict[str, dict[str, int]]]":
    """Merge model and dataset sections into {section: {value: counts}}."""

    merged: dict[str, dict[str, dict[str, int]]] = {}

    # Preserve section order: models file first, then any extra sections
    # only present in the datasets file.
    ordered_sections: list[str] = list(models_sections.keys())
    for section in datasets_sections:
        if section not in ordered_sections:
            ordered_sections.append(section)

    for section in ordered_sections:
        values: dict[str, dict[str, int]] = {}

        for value, count in models_sections.get(section, []):
            values.setdefault(value, {})["model_count"] = count

        for value, count in datasets_sections.get(section, []):
            values.setdefault(value, {})["dataset_count"] = count

        merged[section] = values

    return merged


# ---------------------------------------------------------------------------
# Turtle generation
# ---------------------------------------------------------------------------

def write_concept(
    handle,
    local_name: str,
    raw_value: str,
    class_local: str,
    scheme_local: str,
    counts: "dict[str, int]",
) -> None:
    handle.write(f"dlt:{local_name} a skos:Concept, dlo:{class_local} ;\n")
    handle.write(f'    skos:prefLabel "{turtle_literal(humanize_label(raw_value))}"@en ;\n')

    handle.write(f"    skos:topConceptOf dlt:{scheme_local} ;\n")
    handle.write(f"    skos:inScheme dlt:{scheme_local} .\n\n")


def build_thesaurus(
    models_path: Path,
    datasets_path: Path,
    output_path: Path,
) -> Path:
    models_sections = parse_prefix_file(models_path)
    datasets_sections = parse_prefix_file(datasets_path)
    merged = merge_sections(models_sections, datasets_sections)

    os.makedirs(output_path.parent, exist_ok=True)
    used_names: set[str] = set()
    canonilize: dict[str, str] = {}

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
        handle.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        handle.write("@prefix dlo: <http://ns.inria.fr/datalens/ontology/> .\n")
        handle.write("@prefix dlt: <http://ns.inria.fr/datalens/thesaurus/> .\n\n")

        for section, values in merged.items():
            canonilize_section = {}
            class_local = pascal_case(section)
            scheme_local = f"{class_local}Scheme"
            scheme_label = humanize_label(section)

            handle.write(f"dlt:{scheme_local} a skos:ConceptScheme ;\n")
            handle.write(f'    skos:prefLabel "{turtle_literal(scheme_label)}"@en ;\n')
            handle.write(
                f'    skos:definition "Controlled vocabulary for the '
                f'\'{turtle_literal(scheme_label)}\' prefix values found across models and datasets."@en .\n\n'
            )

            if not values:
                continue

            # Order by combined popularity (models + datasets), most frequent first.
            ordered_values = sorted(
                values.items(),
                key=lambda item: item[1].get("model_count", 0) + item[1].get("dataset_count", 0),
                reverse=True,
            )

            for raw_value, counts in ordered_values:
                local_name = make_unique_local_name(raw_value, used_names)
                canonilize_section[raw_value] = local_name
                write_concept(
                    handle=handle,
                    local_name=local_name,
                    raw_value=raw_value,
                    class_local=class_local,
                    scheme_local=scheme_local,
                    counts=counts,
                )

            canonilize[section] = canonilize_section

            canonilize_path = Path("ontology") / f"kaggle_canonilize.json"
            with canonilize_path.open("w", encoding="utf-8") as canon_handle:
                json.dump(canonilize, canon_handle, indent=2, ensure_ascii=False)

            return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a SKOS thesaurus from all_prefix_values_models.txt and "
            "all_prefix_values_datasets.txt (one ConceptScheme per prefix section)."
        )
    )
    parser.add_argument(
        "--models-input",
        type=Path,
        default=DEFAULT_MODELS_INPUT,
        help="Path to all_prefix_values_models.txt",
    )
    parser.add_argument(
        "--datasets-input",
        type=Path,
        default=DEFAULT_DATASETS_INPUT,
        help="Path to all_prefix_values_datasets.txt",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated Turtle file",
    )
    args = parser.parse_args()

    if not args.models_input.exists() and not args.datasets_input.exists():
        raise FileNotFoundError("Neither input file could be found.")

    output_path = build_thesaurus(args.models_input, args.datasets_input, args.output)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
