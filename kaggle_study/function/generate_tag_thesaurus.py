#!/usr/bin/env python3
"""Generate a SKOS thesaurus fragment for model architectures and model types.

The script reads the statistics file produced by scripts/extract_model_config_stats.py
and converts its architecture and model type sections into a Turtle thesaurus file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path


DEFAULT_INPUT = Path(os.getcwd()) / "tag_analysis" / "model_config_stats_all.txt"
DEFAULT_OUTPUT = Path(os.getcwd()) / "ontology" / "model_config_thesaurus_2.ttl"
DEFAULT_DESCRIPTIONS = Path(os.getcwd()) / "hf_model_descriptions.json"

CATEGORY_MAPPING = {
    "subject": ("SubjectScheme", "Subject"),
    "health and fitness": ("HealthAndFitnessScheme", "HealthAndFitness"),
    "geography and places": ("GeographyAndPlacesScheme", "GeographyAndPlaces"),
    "technique": ("TechniqueScheme", "Technique"),
    "data type": ("DataTypeScheme", "DataType"),
    "audience": ("AudienceScheme", "Audience"),
    "analysis": ("AnalysisScheme", "Analysis"),
    "task": ("TaskScheme", "Task"),
    "packages": ("PackageScheme", "Package"),
    "algorithms": ("AlgorithmScheme", "Algorithm"),
    "admin": ("AdminScheme", "Admin"),
    "language": ("LanguageScheme", "Language"),
    "architecture": ("ArchitectureScheme", "Architecture"),
}


def parse_stats_file(stats_path: Path) -> tuple[Counter[str], Counter[str]]:
    """Parse the counts written by extract_model_config_stats.py."""

    architecture_counts: Counter[str] = Counter()
    model_type_counts: Counter[str] = Counter()
    current_section: str | None = None

    with stats_path.open("r", encoding="utf-8", errors="replace") as stats_file:
        for raw_line in stats_file:
            line = raw_line.strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered == "architectures in config:":
                current_section = "architectures"
                continue
            if lowered == "model types in config:":
                current_section = "model_types"
                continue

            if current_section is None or "\t" not in line:
                continue

            value, count_text = line.rsplit("\t", 1)
            value = value.strip()
            if not value:
                continue

            try:
                count = int(count_text.strip())
            except ValueError:
                continue

            if current_section == "architectures":
                architecture_counts[value] += count
            else:
                model_type_counts[value] += count

    return architecture_counts, model_type_counts


def normalize_key(value: str) -> str:
    """Normalize identifiers so different slug styles can be matched."""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def load_descriptions(
    descriptions_path: Path | None,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Load descriptions preserving JSON order."""

    if descriptions_path is None or not descriptions_path.exists():
        return {}, []

    with descriptions_path.open("r", encoding="utf-8", errors="replace") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        return {}, []

    descriptions: dict[str, dict[str, str]] = {}
    ordered_keys: list[str] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        model = item.get("model")
        description = item.get("description")
        source = item.get("source")

        if (
            isinstance(model, str)
            and isinstance(description, str)
            and description.strip()
        ):
            key = normalize_key(model)
            descriptions[key] = {
                "model": model,
                "description": description.strip(),
                "source": source if isinstance(source, str) else "",
            }
            ordered_keys.append(key)

    return descriptions, ordered_keys

def humanize_label(value: str) -> str:
    """Create a human-readable label from a Hugging Face identifier."""

    text = value.strip()

    # qwen3_5 -> qwen3.5
    text = re.sub(r"(\d+)_(\d+)", r"\1.\2", text)

    # Remaining separators
    text = text.replace("_", " ").replace("-", " ")

    # Split camel case
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)

    # step1 -> step 1
    text = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", text)

    # 3Moe -> 3 Moe
    text = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Capitalize each word while preserving decimal numbers
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


def turtle_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


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

def implementation_iri(value: str) -> str:
    """Return a valid Turtle local name while preserving the original name."""

    iri = value.strip()

    # caractères interdits
    iri = iri.replace(" ", "_")
    iri = iri.replace("+", "_plus_")
    iri = iri.replace("/", "_")
    iri = iri.replace("\\", "_")
    iri = iri.replace(":", "_")
    iri = iri.replace(".", "_")
    iri = iri.replace("(", "_")
    iri = iri.replace(")", "_")
    iri = iri.replace(",", "_")

    iri = re.sub(r"[^A-Za-z0-9_-]", "_", iri)
    iri = re.sub(r"_+", "_", iri).strip("_")

    # un nom local ne devrait pas commencer par un chiffre
    if iri and iri[0].isdigit():
        iri = "Model_" + iri

    return iri

def make_unique_implementation_iri(
    raw_value: str,
    used_names: set[str],
) -> str:

    base = implementation_iri(raw_value)

    if base not in used_names:
        used_names.add(base)
        return base

    i = 2
    while True:
        candidate = f"{base}{i}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        i += 1

def get_concept_local_name(label: str, category: str) -> str:
    """
    Génère le nom local d'un concept.

    Exemples
    --------
    task + Audio Classification
        -> TaskAudioClassification

    subject + Biology
        -> SubjectBiology
    """

    _, class_name = CATEGORY_MAPPING[category]

    return f"{pascal_case(label)}"

def write_concept(
    handle,
    label,
    info,
    category,
    scheme_name,
    canonilize_section: dict[str, str],
    parent=None,
):
    local_name = get_concept_local_name(label, category)

    canonilize_section[label] = local_name

    handle.write(f"dlt:{local_name} a skos:Concept, dlo:{CATEGORY_MAPPING[category][1]} ;\n")
    handle.write(f'    skos:prefLabel "{turtle_literal(label)}"@en ;\n')

    definition = info.get("description")
    if definition:
        handle.write(
            f'    skos:definition "{turtle_literal(definition)}"@en ;\n'
        )

    handle.write(f"    skos:inScheme dlt:{scheme_name}")

    if parent is not None:
        handle.write(f" ;\n    skos:broader dlt:{parent}")
    else:
        handle.write(f" ;\n    skos:topConceptOf dlt:{scheme_name}")

    handle.write(" .\n\n")

    for child_label, child_info in sorted(
        info.get("children", {}).items(),
        key=lambda x: x[0].lower(),
    ):
        child_name = get_concept_local_name(child_label, category)

        handle.write(
            f"dlt:{local_name} skos:narrower dlt:{child_name} .\n\n"
        )

        write_concept(
            handle,
            child_label,
            child_info,
            category,
            scheme_name,            
            canonilize_section,
            local_name,
        )

def write_scheme(
    handle,
    category,
    category_info,
):
    scheme_name, class_name = CATEGORY_MAPPING[category]
    handle.write(
        f"dlt:{scheme_name} a skos:ConceptScheme, dlo:{class_name} ;\n"
    )

    handle.write(
        f'    skos:prefLabel "{class_name}"@en ;\n'
    )

    handle.write(
        f'    skos:definition "{class_name} concept scheme."@en .\n\n'
    )
    canonilize_section: dict[str, str] = {}
    for label, info in sorted(
        category_info["children"].items(),
        key=lambda x: x[0].lower(),
    ):

        local_name = get_concept_local_name(label, category)
        handle.write(
            f"dlt:{scheme_name} skos:hasTopConcept dlt:{local_name} .\n\n"
        )

        write_concept(
            handle,
            label,
            info,
            category,
            scheme_name,
            canonilize_section
        )
    
    return canonilize_section


def build_thesaurus(tags_path: Path, output_path: Path) -> Path:

    with tags_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(output_path.parent, exist_ok=True)
    canonilize: dict[str, str] = {}
    with output_path.open("w", encoding="utf-8") as handle:

        handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
        handle.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        handle.write("@prefix dlo: <http://ns.inria.fr/datalens/ontology/> .\n")
        handle.write("@prefix dlt: <http://ns.inria.fr/datalens/thesaurus/> .\n\n")

        for category in CATEGORY_MAPPING:
            if category not in data:
                continue

            canonilize_section: dict[str, str] = write_scheme(
                handle,
                category,
                data[category],
            )

            canonilize[category] = canonilize_section

    canonilize_path = Path("ontology") / f"kaggle_canonilize.json"
    with canonilize_path.open("w", encoding="utf-8") as canon_handle:
        json.dump(canonilize, canon_handle, indent=2, ensure_ascii=False)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a SKOS thesaurus fragment for model architectures and model types."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to model_config_stats_all.txt",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated Turtle file",
    )
    parser.add_argument(
        "--descriptions",
        type=Path,
        default=DEFAULT_DESCRIPTIONS,
        help="Optional path to hf_model_descriptions.json",
    )
    args = parser.parse_args()

    output_path = build_thesaurus(
    Path("huggingface_study/tags.json"),
    Path("ontology/kaggle_tags.ttl"),
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()