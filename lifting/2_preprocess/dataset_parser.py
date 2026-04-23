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
}

SPDX_CANONICAL_IDS = {
    "apache-2.0": "Apache-2.0",
    "afl-3.0": "AFL-3.0",
    "agpl-3.0": "AGPL-3.0-only",
    "artistic-2.0": "Artistic-2.0",
    "bsl-1.0": "BSL-1.0",
    "bsd": "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-3-clause-clear": "BSD-3-Clause",
    "cc": None,
    "cc-by-2.0": None,
    "cc-by-2.5": None,
    "cc-by-3.0": None,
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-nc-2.0": None,
    "cc-by-nc-3.0": None,
    "cc-by-nc-4.0": None,
    "cc-by-nc-nd-3.0": None,
    "cc-by-nc-nd-4.0": None,
    "cc-by-nc-sa-2.0": None,
    "cc-by-nc-sa-3.0": None,
    "cc-by-nc-sa-4.0": None,
    "cc-by-nd-4.0": None,
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-sa-3.0": None,
    "cc0-1.0": "CC0-1.0",
    "cdla-permissive-1.0": "CDLA-Permissive-1.0",
    "cdla-permissive-2.0": "CDLA-Permissive-2.0",
    "cdla-sharing-1.0": "CDLA-Sharing-1.0",
    "ecl-2.0": "ECL-2.0",
    "epl-1.0": "EPL-1.0",
    "epl-2.0": "EPL-2.0",
    "eupl-1.1": "EUPL-1.1",
    "eupl-1.2": "EUPL-1.2",
    "gfdl": "GFDL-1.3-or-later",
    "gpl": "GPL-3.0-only",
    "gpl-2.0": "GPL-2.0-only",
    "gpl-2.0-only": "GPL-2.0-only",
    "gpl-3.0": "GPL-3.0-only",
    "gpl-3.0-only": "GPL-3.0-only",
    "isc": "ISC",
    "lgpl": "LGPL-2.1-only",
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-2.1-only": "LGPL-2.1-only",
    "lgpl-3.0": "LGPL-3.0-only",
    "lgpl-3.0-only": "LGPL-3.0-only",
    "lppl-1.3c": "LPPL-1.3c",
    "mit": "MIT",
    "mpl-2.0": "MPL-2.0",
    "ncsa": "NCSA",
    "odbl": "ODbL-1.0",
    "odc-by": "ODC-By-1.0",
    "ofl-1.1": "OFL-1.1",
    "osl-3.0": "OSL-3.0",
    "pddl": "PDDL-1.0",
    "postgresql": "PostgreSQL",
    "unlicense": "Unlicense",
    "wtfpl": "WTFPL",
    "zlib": "Zlib",
}

FORMAT_IANA_MEDIA_TYPES = {
    "agent-traces": None,
    "arrow": "application/vnd.apache.arrow.file",
    "audiofolder": None,
    "json": "application/json",
    "csv": "text/csv",
    "imagefolder": None,
    "optimized-parquet": "application/vnd.apache.parquet",
    "parquet": "application/vnd.apache.parquet",
    "soundfolder": None,
    "text": "text/plain",
    "webdataset": None,
}

REGION_ALIAS_ALPHA2 = {
    "uk": "gb",
}

NS_LEXVO_ISO639_1 = "https://lexvo.org/id/iso639-1/"
NS_LEXVO_ISO639_3 = "https://lexvo.org/id/iso639-3/"
NS_ISO3166 = "https://www.iso.org/obp/ui/#iso:code:3166:"
NS_IANA_MEDIA_TYPES = "https://www.iana.org/assignments/media-types/"
NS_SPDX_LICENSES = "https://spdx.org/licenses/"

CC_LICENSE_URIS = {
    "cc": "http://creativecommons.org/licenses/",
    "cc0-1.0": "http://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-2.0": "http://creativecommons.org/licenses/by/2.0/",
    "cc-by-2.5": "http://creativecommons.org/licenses/by/2.5/",
    "cc-by-3.0": "http://creativecommons.org/licenses/by/3.0/",
    "cc-by-4.0": "http://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-3.0": "http://creativecommons.org/licenses/by-sa/3.0/",
    "cc-by-sa-4.0": "http://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc-2.0": "http://creativecommons.org/licenses/by-nc/2.0/",
    "cc-by-nc-3.0": "http://creativecommons.org/licenses/by-nc/3.0/",
    "cc-by-nc-4.0": "http://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa-2.0": "http://creativecommons.org/licenses/by-nc-sa/2.0/",
    "cc-by-nc-sa-3.0": "http://creativecommons.org/licenses/by-nc-sa/3.0/",
    "cc-by-nc-sa-4.0": "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nc-nd-3.0": "http://creativecommons.org/licenses/by-nc-nd/3.0/",
    "cc-by-nc-nd-4.0": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
    "cc-by-nd-4.0": "http://creativecommons.org/licenses/by-nd/4.0/",
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


def load_allowed_labels(file_name: str, root_key: str) -> set[str]:
    path = Path(__file__).parent / file_name
    if not path.exists():
        return set()

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return set()

    labels: set[str] = set()
    items = data.get(root_key, []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        return set()

    for item in items:
        if not isinstance(item, dict):
            continue
        label = normalize_string(item.get("label"))
        if label:
            labels.add(label.lower())

        identifier = normalize_string(item.get("id"))
        if identifier and ":" in identifier:
            labels.add(identifier.split(":", 1)[1].lower())

    return labels


LICENSE_LABELS = load_allowed_labels("license.json", "license")
FORMAT_LABELS = load_allowed_labels("format.json", "format")


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
        normalized_tags.append(SPACE_AROUND_COLON.sub(":", tag).lower())

    deduped_tags = dedupe(normalized_tags)
    tags: list[str] = []
    for tag in deduped_tags:
        if tag.startswith("size_categories:"):
            prefix, value = tag.split(":", 1)
            normalized_size = SIZE_CATEGORY_UNITS.sub(lambda m: m.group(1).upper(), value)
            tags.append(f"{prefix}:{normalized_size}")
        else:
            tags.append(tag)

    removed_count = len(normalized_tags) - len(deduped_tags)
    return tags, removed_count


def get_tag_values(tags: list[str], prefix: str) -> list[str]:
    values: list[str] = []
    for tag in tags:
        if tag.startswith(prefix):
            value = normalize_string(tag.split(":", 1)[1])
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
            if FORMAT_LABELS and token not in FORMAT_LABELS:
                continue
            if "/" in token:
                uri = f"{NS_IANA_MEDIA_TYPES}{token}"
            else:
                media_type = FORMAT_IANA_MEDIA_TYPES.get(token)
                if media_type:
                    uri = f"{NS_IANA_MEDIA_TYPES}{media_type}"

        elif kind == "license":
            if LICENSE_LABELS and token not in LICENSE_LABELS:
                continue
            if token not in {"unknown", "other"}:
                if token in CC_LICENSE_URIS:
                    uri = CC_LICENSE_URIS[token]
                    uris.append(uri)
                    continue
                spdx_id = SPDX_CANONICAL_IDS.get(token)
                if not spdx_id and re.fullmatch(r"[a-z0-9][a-z0-9-.+]*", token):
                    spdx_id = token.upper().replace(".0-ONLY", ".0-only")
                if spdx_id:
                    uri = f"{NS_SPDX_LICENSES}{spdx_id}.html"

        if uri:
            uris.append(uri)

    return dedupe(uris)


def normalize_source_datasets(value: Any) -> list[str]:
    if value == "original":
        return []

    sources: list[str] = []
    for item in to_list(value):
        if "|" in item:
            source = normalize_string(item.split("|", 1)[1])
            if source:
                sources.append(source)
        else:
            sources.append(item)
    return dedupe(sources)


def parse(json_obj: dict[str, Any]) -> tuple[dict[str, Any], int]:
    parsed = dict(json_obj)

    parsed["id"] = normalize_string(parsed.get("id"))
    parsed["author"] = normalize_string(parsed.get("author"))
    parsed["description"] = normalize_string(parsed.get("description"))
    parsed["paperswithcode_id"] = normalize_string(parsed.get("paperswithcode_id"))
    parsed["private"] = normalize_boolean(parsed.get("private"))
    parsed["gated"] = normalize_boolean(parsed.get("gated"))
    parsed["disabled"] = normalize_boolean(parsed.get("disabled"))
    tags, removed_count = normalize_and_dedupe_tags(parsed.get("tags", []))
    parsed["tags"] = tags

    task_ids = dedupe(get_tag_values(tags, "task_ids:") + to_list(parsed.get("task_ids")))
    task_categories = dedupe(get_tag_values(tags, "task_categories:") + to_list(parsed.get("task_categories")))
    modality_values = get_tag_values(tags, "modality:") + to_list(parsed.get("modality")) + to_list(parsed.get("modalities"))
    modalities = canonicalize_modalities(modality_values)
    size_categories = dedupe(get_tag_values(tags, "size_categories:") + to_list(parsed.get("size_categories")))

    languages = dedupe(
        [v.lower().replace("_", "-") for v in (get_tag_values(tags, "language:") + to_list(parsed.get("language")) + to_list(parsed.get("languages")))]
    )
    regions = dedupe(
        [v.lower() for v in (get_tag_values(tags, "region:") + to_list(parsed.get("region")) + to_list(parsed.get("regions")))]
    )
    formats = dedupe(
        [v.lower() for v in (get_tag_values(tags, "format:") + to_list(parsed.get("format")) + to_list(parsed.get("formats")))]
    )
    licenses = dedupe(
        [v.lower() for v in (get_tag_values(tags, "license:") + to_list(parsed.get("license")) + to_list(parsed.get("licenses")))]
    )

    annotation_value = parsed.get("annotation")
    if isinstance(annotation_value, list):
        annotation = normalize_string(" | ".join(to_list(annotation_value)))
    else:
        annotation = normalize_string(annotation_value)

    parsed["task_ids"] = task_ids
    parsed["task_categories"] = task_categories
    parsed["modalities"] = modalities
    parsed["size_categories"] = size_categories
    parsed["source_datasets_values"] = normalize_source_datasets(parsed.get("source_datasets"))
    parsed["language_uris"] = build_uris(languages, "language")
    parsed["region_uris"] = build_uris(regions, "region")
    parsed["format_uris"] = build_uris(formats, "format")
    parsed["license_uris"] = build_uris(licenses, "license")
    parsed["annotation"] = annotation
    parsed["annotation_hash16"] = hash16(f"annotation:{annotation}") if annotation else None

    parsed["dataset_hash16"] = hash16(f"dataset:{parsed.get('id')}") if parsed.get("id") else None
    parsed["distribution_hash16"] = hash16(f"distribution:{parsed.get('id')}") if parsed.get("id") else None
    parsed["creator_hash16"] = hash16(f"creator:{parsed.get('author')}") if parsed.get("author") else None
    parsed["article_hash16"] = hash16(f"pwc:{parsed.get('paperswithcode_id')}") if parsed.get("paperswithcode_id") else None

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
            "Parser unifie pour les datasets Hugging Face: normalisation, enrichissement "
            "thesaurus et generation des champs techniques pour XR2RML."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "datasets.json",
        help="Fichier JSON source (par defaut: datasets.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "datasets_parsed.json",
        help="Fichier JSON de sortie (par defaut: datasets_parsed.json)",
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
