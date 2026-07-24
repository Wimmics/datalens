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

_ARCHITECTURE_SUFFIXES = [
    "ForConditionalGenerationWithPointer",
    "ForConditionalGeneration",
    "ForSequenceClassification",
    "ForTokenClassification",
    "ForQuestionAnswering",
    "ForCausalLM",
    "ForMaskedLM",
    "ForMultipleChoice",
    "ForImageClassification",
    "ForAudioClassification",
    "ForVideoClassification",
    "ForSemanticSegmentation",
    "ForObjectDetection",
    "ForSpeechClassification",
    "ForPreTraining",
    "ForCTC",
    "ForTextToSpeech",
    "LMHeadModel",
    "TextModel",
    "VisionModel",
    "AudioModel",
    "Model",
]


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

def architecture_description_candidates(raw_value: str) -> list[str]:
    """Generate candidate slugs for a model architecture or model type."""

    candidates = [raw_value]
    cleaned = raw_value.strip()
    for suffix in _ARCHITECTURE_SUFFIXES:
        if cleaned.endswith(suffix):
            candidates.append(cleaned[: -len(suffix)])

    if cleaned.endswith("For"):  # defensive, should rarely happen
        candidates.append(cleaned[:-3])

    normalized_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip("_- ")
        if not candidate:
            continue
        normalized = normalize_key(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            normalized_candidates.append(normalized)
    return normalized_candidates


def resolve_description(
    raw_value: str,
    descriptions: dict[str, dict[str, str]],
) -> dict[str, str] | None:

    for candidate in architecture_description_candidates(raw_value):
        if candidate in descriptions:
            return descriptions[candidate]

    return None

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

def write_scheme(
    handle,
    scheme_name: str,
    scheme_label: str,
    scheme_definition: str,
    concept_class: str | None,
    counts: Counter[str],
    used_names: set[str],
    descriptions: dict[str, str],
    description_order: list[str],
    humanize_labels: bool = True,
) -> None:
    
    if description_order and descriptions:

        ordered_items = []
        seen: set[str] = set()

        # 1. Tous les modèles documentés (ordre du JSON)
        for key in description_order:
            info = descriptions[key]

            raw_value = info["model"]

            ordered_items.append((raw_value, counts.get(raw_value, 0)))
            seen.add(normalize_key(raw_value))

        # 2. Tous les autres modèles présents dans les stats
        remaining = []

        for raw_value, count in counts.items():
            if normalize_key(raw_value) not in seen:
                remaining.append((raw_value, count))

        ordered_items.extend(
            sorted(remaining, key=lambda item: item[0].lower())
        )

    else:
        ordered_items = sorted(
            counts.items(),
            key=lambda item: item[0].lower(),
        )

    concepts: list[tuple[str, str, int]] = []

    for raw_value, count in ordered_items:
        local_name = (
            make_unique_local_name(raw_value, used_names)
            if humanize_labels
            else make_unique_implementation_iri(raw_value, used_names)
        )
        concepts.append((local_name, raw_value, count))

    handle.write(f"dlt:{scheme_name} a skos:ConceptScheme ;\n")
    handle.write(f'    skos:prefLabel "{turtle_literal(scheme_label)}"@en ;\n')
    handle.write(f'    skos:definition "{turtle_literal(scheme_definition)}"@en .\n\n')

    for local_name, raw_value, count in concepts:
        label = raw_value if not humanize_labels else humanize_label(raw_value)
        handle.write(f"dlt:{local_name} a skos:Concept")
        if concept_class:
            handle.write(f", {concept_class}")
        handle.write(" ;\n")
        handle.write(f'    skos:prefLabel "{turtle_literal(label)}"@en ;\n')        
        entry = resolve_description(raw_value, descriptions)

        if entry:
            handle.write(
                f'    skos:definition "{turtle_literal(entry["description"])}"@en ;\n'
            )

            if entry["source"]:
                handle.write(
                    f'    skos:seeAlso <{entry["source"]}> ;\n'
                )
        handle.write(f'    skos:inScheme dlt:{scheme_name} .\n\n')



def build_thesaurus(stats_path: Path, output_path: Path, descriptions_path: Path | None) -> Path:
    architecture_counts, model_type_counts = parse_stats_file(stats_path)
    descriptions, description_order = load_descriptions(descriptions_path)

    os.makedirs(output_path.parent, exist_ok=True)
    used_names: set[str] = set()

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        handle.write("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n")
        handle.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        handle.write("@prefix dlo: <http://ns.inria.fr/datalens/ontology/> .\n")
        handle.write("@prefix dlt: <http://ns.inria.fr/datalens/thesaurus/> .\n\n")

        write_scheme(
            handle=handle,
            scheme_name="ModelFamilyScheme",
            scheme_label="Model Family Scheme",
            scheme_definition="Controlled vocabulary for model families.",
            concept_class="dlo:ModelFamily",
            counts=model_type_counts,
            used_names=used_names,
            descriptions=descriptions,
            description_order=description_order,
            humanize_labels=True
        )

        write_scheme(
            handle=handle,
            scheme_name="ModelImplementationScheme",
            scheme_label="Model Implementation Scheme",
            scheme_definition="Controlled vocabulary for model family implementations.",
            concept_class="dlo:Implementation",
            counts=architecture_counts,
            used_names=used_names,
            descriptions={},  # descriptions are not available for architectures
            description_order=[],
            humanize_labels=False
        )



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

    if not args.input.exists():
        raise FileNotFoundError(f"Stats file not found: {args.input}")

    output_path = build_thesaurus(args.input, args.output, args.descriptions)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()