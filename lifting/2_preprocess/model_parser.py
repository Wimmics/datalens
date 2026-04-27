from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SPACE_AROUND_COLON = re.compile(r"\s*:\s*")
MULTI_SPACE = re.compile(r"\s+")
LANGUAGE_2 = re.compile(r"^[a-z]{2}$")
LANGUAGE_3 = re.compile(r"^[a-z]{3}$")
LANGUAGE_BCP47 = re.compile(r"^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$")
REGION_ALPHA2 = re.compile(r"^[a-z]{2}$")

MODALITY_CANONICAL = {
    "3d": "3D",
    "text": "Text",
    "tabular": "Tabular",
    "image": "Image",
    "audio": "Audio",
    "video": "Video",
    "timeseries": "TimeSeries",
    "time_series": "TimeSeries",
    "time-series": "TimeSeries",
    "multimodal": "Multimodal",
}

SPDX_CANONICAL_IDS = {
    "apache-2.0": "Apache-2.0",
    "afl-3.0": "AFL-3.0",
    "agpl-3.0": "AGPL-3.0-only",
    "artistic-2.0": "Artistic-2.0",
    "bsd": "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-3-clause-clear": "BSD-3-Clause",
    "cc": None,
    "cc-by-2.0": None,
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-nc-2.0": None,
    "cc-by-nc-3.0": None,
    "cc-by-nc-4.0": None,
    "cc-by-nc-nd-4.0": None,
    "cc-by-nc-sa-4.0": None,
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc0-1.0": "CC0-1.0",
    "cdla-permissive-2.0": "CDLA-Permissive-2.0",
    "ecl-2.0": "ECL-2.0",
    "gpl": "GPL-3.0-only",
    "gpl-2.0": "GPL-2.0-only",
    "gpl-3.0": "GPL-3.0-only",
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-3.0": "LGPL-3.0-only",
    "mit": "MIT",
    "pddl": "PDDL-1.0",
    "unlicense": "Unlicense",
    "wtfpl": "WTFPL",
}

FORMAT_IANA_MEDIA_TYPES = {
    "arrow": "application/vnd.apache.arrow.file",
    "json": "application/json",
    "csv": "text/csv",
    "parquet": "application/vnd.apache.parquet",
    "text": "text/plain",
}

REGION_ALIAS_ALPHA2 = {
    "uk": "gb",
}

KNOWN_LIBRARY_TAGS = {
    "transformers",
    "vllm",
    "diffusers",
    "sentence-transformers",
    "pytorch",
    "tensorflow",
    "keras",
    "flax",
    "mlx",
}

NS_LEXVO_ISO639_1 = "https://lexvo.org/id/iso639-1/"
NS_LEXVO_ISO639_3 = "https://lexvo.org/id/iso639-3/"
NS_ISO3166 = "https://www.iso.org/obp/ui/#iso:code:3166:"
NS_IANA_MEDIA_TYPES = "https://www.iana.org/assignments/media-types/"
NS_SPDX_LICENSES = "https://spdx.org/licenses/"

RESOURCE_BASE = "http://example.org/datalens_o/data#"

CC_LICENSE_URIS = {
    "cc": "http://creativecommons.org/licenses/",
    "cc0-1.0": "http://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-2.0": "http://creativecommons.org/licenses/by/2.0/",
    "cc-by-4.0": "http://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-4.0": "http://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc-2.0": "http://creativecommons.org/licenses/by-nc/2.0/",
    "cc-by-nc-3.0": "http://creativecommons.org/licenses/by-nc/3.0/",
    "cc-by-nc-4.0": "http://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa-4.0": "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nc-nd-4.0": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
}


def normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value) if not isinstance(value, str) else value
    text = MULTI_SPACE.sub(" ", text).strip()
    return text or None


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


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in (normalize_string(item) for item in value) if v]
    single = normalize_string(value)
    return [single] if single else []


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def hash16(value: Any) -> str | None:
    text = normalize_string(value)
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def normalize_and_dedupe_tags(raw_tags: Any) -> tuple[list[str], int]:
    if not isinstance(raw_tags, list):
        return [], 0

    normalized_tags: list[str] = []
    for item in raw_tags:
        tag = normalize_string(item)
        if not tag:
            continue
        normalized_tags.append(SPACE_AROUND_COLON.sub(":", tag))

    seen_lower: set[str] = set()
    deduped_tags: list[str] = []
    for tag in normalized_tags:
        key = tag.lower()
        if key not in seen_lower:
            seen_lower.add(key)
            deduped_tags.append(tag)

    removed_count = len(normalized_tags) - len(deduped_tags)
    return deduped_tags, removed_count


def get_tag_values(tags: list[str], prefix: str) -> list[str]:
    values: list[str] = []
    normalized_prefix = prefix.lower()
    for tag in tags:
        lower_tag = tag.lower()
        if lower_tag.startswith(normalized_prefix):
            value = normalize_string(tag[len(prefix) :])
            if value:
                values.append(value)
    return dedupe(values)


def canonicalize_modalities(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        key = value.lower().replace(" ", "").replace("_", "-")
        canonical = MODALITY_CANONICAL.get(key, value.replace("_", "-").title().replace("-", ""))
        output.append(canonical)
    return dedupe(output)


def build_uris(values: list[str], kind: str) -> list[str]:
    uris: list[str] = []
    for value in values:
        token = value.lower()
        uri = None

        if kind == "language":
            token = token.replace("_", "-")
            if LANGUAGE_BCP47.fullmatch(token):
                primary = token.split("-", 1)[0]
                if LANGUAGE_2.fullmatch(primary):
                    uri = f"{NS_LEXVO_ISO639_1}{primary}"
                elif LANGUAGE_3.fullmatch(primary):
                    uri = f"{NS_LEXVO_ISO639_3}{primary}"

        elif kind == "region":
            if token not in {"unknown", "other"}:
                alpha2 = REGION_ALIAS_ALPHA2.get(token, token)
                if REGION_ALPHA2.fullmatch(alpha2):
                    uri = f"{NS_ISO3166}{alpha2.upper()}"

        elif kind == "format":
            if "/" in token:
                uri = f"{NS_IANA_MEDIA_TYPES}{token}"
            else:
                media_type = FORMAT_IANA_MEDIA_TYPES.get(token)
                if media_type:
                    uri = f"{NS_IANA_MEDIA_TYPES}{media_type}"

        elif kind == "license":
            if token not in {"unknown", "other"}:
                if token in CC_LICENSE_URIS:
                    uris.append(CC_LICENSE_URIS[token])
                    continue
                spdx_id = SPDX_CANONICAL_IDS.get(token)
                if spdx_id:
                    uri = f"{NS_SPDX_LICENSES}{spdx_id}.html"

        if uri:
            uris.append(uri)

    return dedupe(uris)


def model_id_to_iri(model_id: str | None) -> str | None:
    normalized_id = normalize_string(model_id)
    if not normalized_id:
        return None
    if normalized_id.startswith("http://") or normalized_id.startswith("https://"):
        return normalized_id
    model_hash = hash16(f"model:{normalized_id}")
    return f"{RESOURCE_BASE}model/{model_hash}" if model_hash else None


def dataset_id_to_iri(dataset_id: str | None) -> str | None:
    normalized_id = normalize_string(dataset_id)
    if not normalized_id:
        return None
    if normalized_id.startswith("http://") or normalized_id.startswith("https://"):
        return normalized_id
    dataset_hash = hash16(f"dataset:{normalized_id}")
    return f"{RESOURCE_BASE}dataset/{dataset_hash}" if dataset_hash else None


def author_from_hf_id(resource_id: str | None) -> str | None:
    normalized_id = normalize_string(resource_id)
    if not normalized_id or "/" not in normalized_id:
        return None
    owner, _, _ = normalized_id.partition("/")
    return normalize_string(owner)


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def infer_language_tokens(tags: list[str], explicit_values: list[str]) -> list[str]:
    tokens: list[str] = []
    for value in explicit_values:
        candidate = value.lower().replace("_", "-")
        primary = candidate.split("-", 1)[0]
        if LANGUAGE_2.fullmatch(primary) or LANGUAGE_3.fullmatch(primary):
            tokens.append(candidate)

    for tag in tags:
        if ":" in tag:
            continue
        candidate = tag.lower().replace("_", "-")
        if LANGUAGE_2.fullmatch(candidate):
            tokens.append(candidate)
    return dedupe(tokens)


def infer_modalities(tags: list[str], pipeline_tag: str | None, explicit_values: list[str]) -> list[str]:
    raw: list[str] = list(explicit_values)

    tag_to_modality = {
        "audio": "Audio",
        "image": "Image",
        "video": "Video",
        "text": "Text",
        "tabular": "Tabular",
        "timeseries": "TimeSeries",
        "time-series": "TimeSeries",
        "3d": "3D",
        "multimodal": "Multimodal",
    }
    for tag in tags:
        mapped = tag_to_modality.get(tag)
        if mapped:
            raw.append(mapped)

    pipe = normalize_string(pipeline_tag)
    if pipe:
        p = pipe.lower()
        if p.startswith("text") or p in {"conversational", "fill-mask", "token-classification"}:
            raw.append("Text")
        if p.startswith("image"):
            raw.append("Image")
        if p.startswith("audio") or "speech" in p:
            raw.append("Audio")
        if p == "text-to-speech":
            raw.extend(["Text", "Audio"])
        if p == "image-text-to-text":
            raw.extend(["Image", "Text"])

    return canonicalize_modalities(raw)


def parse_base_model_tags(tags: list[str], parsed: dict[str, Any]) -> None:
    plain_ids: list[str] = []
    typed_ids: dict[str, list[str]] = {
        "finetune": [],
        "quantized": [],
        "merge": [],
        "adapter": [],
    }

    for tag in tags:
        lower_tag = tag.lower()
        if not lower_tag.startswith("base_model:"):
            continue
        payload = tag[len("base_model:") :]
        if not payload:
            continue

        left, sep, right = payload.partition(":")
        relation = left.lower()
        if sep and relation in typed_ids and right:
            typed_ids[relation].append(right)
        else:
            plain_ids.append(payload)

    finetuned_ids = dedupe(typed_ids["finetune"])
    quantized_ids = dedupe(typed_ids["quantized"])
    merged_ids = dedupe(typed_ids["merge"])
    adapter_ids = dedupe(typed_ids["adapter"])
    plain_ids = dedupe(plain_ids)

    if plain_ids and not finetuned_ids:
        # Fallback for entries that only expose "base_model:<id>".
        finetuned_ids = plain_ids

    parsed["finetuned_base_model"] = model_id_to_iri(first_or_none(finetuned_ids))
    parsed["quantized_base_model"] = model_id_to_iri(first_or_none(quantized_ids))
    parsed["merged_base_model"] = model_id_to_iri(first_or_none(merged_ids))
    parsed["adapter_base_model"] = model_id_to_iri(first_or_none(adapter_ids))


def compute_article_hash(pwc_id: str | None, dois: list[str], arxivs: list[str]) -> str | None:
    if pwc_id:
        return hash16(f"pwc:{pwc_id}")
    if dois or arxivs:
        payload = {"doi": sorted(dois), "arxiv": sorted(arxivs)}
        return hash16(f"article:{json.dumps(payload, sort_keys=True, ensure_ascii=False)}")
    return None


def parse(json_obj: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parsed = dict(json_obj)

    parsed["id"] = normalize_string(parsed.get("id") or parsed.get("modelId"))
    parsed["author"] = author_from_hf_id(parsed["id"]) or normalize_string(parsed.get("author"))
    parsed["description"] = normalize_string(parsed.get("description"))
    parsed["paperswithcode_id"] = normalize_string(parsed.get("paperswithcode_id"))
    parsed["private"] = normalize_boolean(parsed.get("private"))
    parsed["gated"] = normalize_boolean(parsed.get("gated"))
    parsed["disabled"] = normalize_boolean(parsed.get("disabled"))

    tags, removed_count = normalize_and_dedupe_tags(parsed.get("tags", []))
    parsed["tags"] = tags

    pipeline_tag = normalize_string(parsed.get("pipeline_tag"))

    task_categories = dedupe(get_tag_values(tags, "task_categories:") + to_list(parsed.get("task_categories")))
    if pipeline_tag:
        task_categories.append(pipeline_tag)
        task_categories = dedupe(task_categories)

    explicit_modalities = get_tag_values(tags, "modality:") + to_list(parsed.get("modality")) + to_list(parsed.get("modalities"))
    modalities = infer_modalities(tags, pipeline_tag, explicit_modalities)

    libraries = dedupe(
        get_tag_values(tags, "library:")
        + to_list(parsed.get("library"))
        + to_list(parsed.get("library_name"))
        + [tag for tag in tags if tag in KNOWN_LIBRARY_TAGS]
    )

    region_tokens = dedupe(get_tag_values(tags, "region:") + to_list(parsed.get("region")) + to_list(parsed.get("regions")))
    explicit_language_values = get_tag_values(tags, "language:") + to_list(parsed.get("language")) + to_list(parsed.get("languages"))
    language_tokens = infer_language_tokens(tags, explicit_language_values)

    format_tokens = dedupe(
        get_tag_values(tags, "format:")
        + to_list(parsed.get("format"))
        + to_list(parsed.get("formats"))
        + [tag for tag in tags if tag in {"json", "csv", "parquet", "arrow", "text", "webdataset", "audiofolder", "imagefolder"}]
    )

    license_tokens = dedupe(get_tag_values(tags, "license:") + to_list(parsed.get("license")) + to_list(parsed.get("licenses")))

    dataset_ids = dedupe(get_tag_values(tags, "dataset:") + to_list(parsed.get("dataset")) + to_list(parsed.get("datasets")))
    dataset_iris = dedupe([iri for iri in (dataset_id_to_iri(dataset_id) for dataset_id in dataset_ids) if iri])

    parse_base_model_tags(tags, parsed)

    parsed["task_categories"] = task_categories
    parsed["modalities"] = modalities
    parsed["libraries"] = libraries
    parsed["dataset"] = first_or_none(dataset_iris)
    parsed["datasets"] = dataset_iris
    parsed["language_uris"] = build_uris(language_tokens, "language")
    parsed["region_uris"] = build_uris(region_tokens, "region")
    parsed["format_uris"] = build_uris(format_tokens, "format")
    parsed["license_uris"] = build_uris(license_tokens, "license")

    parsed["doi"] = dedupe(get_tag_values(tags, "doi:") + to_list(parsed.get("doi")))
    parsed["arxiv"] = dedupe(get_tag_values(tags, "arxiv:") + to_list(parsed.get("arxiv")))

    parsed["model_hash16"] = hash16(f"model:{parsed.get('id')}") if parsed.get("id") else None
    parsed["distribution_hash16"] = hash16(f"distribution:{parsed.get('id')}") if parsed.get("id") else None
    parsed["creator_hash16"] = hash16(f"creator:{parsed.get('author')}") if parsed.get("author") else None
    parsed["article_hash16"] = compute_article_hash(parsed.get("paperswithcode_id"), parsed["doi"], parsed["arxiv"])

    # Compatibility with current mapping_models.ttl dataset-named triples maps.
    parsed["dataset_hash16"] = parsed["model_hash16"]

    return parsed, removed_count


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
    parser = argparse.ArgumentParser(
        description=(
            "Parser unifie pour les modeles Hugging Face: normalisation, enrichissement "
            "et generation des champs techniques pour XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "models_new_extract.json",
        help="Fichier JSON source (par defaut: models_new_extract.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "models_parsed.json",
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
