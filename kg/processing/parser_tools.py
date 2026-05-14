import hashlib
import re
from typing import Any

SPACE_AROUND_COLON = re.compile(r"\s*:\s*")
MULTI_SPACE = re.compile(r"\s+")
SIZE_CATEGORY_UNITS = re.compile(r"(?<=\d)([kmbt])\b")
LANGUAGE_2 = re.compile(r"^[a-z]{2}$")
LANGUAGE_3 = re.compile(r"^[a-z]{3}$")
LANGUAGE_BCP47 = re.compile(r"^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$")
REGION_ALPHA2 = re.compile(r"^[a-z]{2}$")

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

REGION_ALIAS_ALPHA2 = {
    "uk": "gb",
}

NS_LEXVO_ISO639_1 = "https://lexvo.org/id/iso639-1/"
NS_LEXVO_ISO639_3 = "https://lexvo.org/id/iso639-3/"
NS_ISO3166 = "https://www.iso.org/obp/ui/#iso:code:3166:"
NS_SPDX_LICENSES = "https://spdx.org/licenses/"
NS_DATALENS_THESAURUS = "http://[namespace]/datalens/thesaurus#"
NS_DATALENS_DATA_LIBRARY = "http://[namespace]/datalens/data#library/"

CC_LICENSE_URIS = {
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

MODEL_LIBRARY_TAGS = {
	"adapter-transformers",
	"allennlp",
	"asteroid",
	"bertopic",
	"coreml",
	"diffusers",
	"executorch",
	"fairseq",
	"fastai",
	"fasttext",
	"flair",
	"gguf",
	"jax",
	"joblib",
	"keras",
	"keras-hub",
	"llamafile",
	"mlx",
	"ml-agents",
	"nemo",
	"onnx",
	"open_clip",
	"openvino",
	"optimum-graphcore",
	"optimum-habana",
	"paddleocr",
	"paddlenlp",
	"paddlepaddle",
	"peft",
	"pyannote-audio",
	"pytorch",
	"sample-factory",
	"safetensors",
	"sentence-transformers",
	"setfit",
	"sklearn",
	"spacy",
	"span-marker",
	"speechbrain",
	"stable-baselines3",
	"stanza",
	"tensorboard",
	"tf",
	"tf-keras",
	"tflite",
	"timm",
	"transformers",
	"transformers-js",
	"univa",
	"unity-sentis",
	"webdataset",
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


def remove_consumed_tags(
    tags: list[str],
    *,
    exact_tags: list[str] | None = None,
    prefixes: list[str] | None = None,
) -> tuple[list[str], int]:
    exact_set = set(exact_tags or [])
    prefix_values = tuple(prefixes or [])

    cleaned_tags: list[str] = []
    removed_count = 0
    for tag in tags:
        should_remove = tag in exact_set or any(tag.startswith(prefix) for prefix in prefix_values)
        if should_remove:
            removed_count += 1
            continue
        cleaned_tags.append(tag)

    return cleaned_tags, removed_count


def get_tag_with_prefix(tags: list[str], prefix: str) -> list[str]:
    values: list[str] = []
    for tag in tags:
        if tag.startswith(prefix):
            value = normalize_string(tag.split(":", 1)[1])
            if value:
                values.append(value)
                tags.remove(tag)
    return dedupe(values)

def fallback_model_libraries(values: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    thesaurus_libraries: list[str] = []
    fallback_instances: list[dict[str, Any]] = []
    seen_fallback_hashes: set[str] = set()
    
    if not isinstance(values, list):
        return [], []
    
    for value in values:
        token = normalize_string(value)
        if not token:
            continue

        normalized = token.lower()
        if normalized in MODEL_LIBRARY_TAGS:
            thesaurus_libraries.append(normalized)
            continue

        library_hash = hash16(normalized)
        if not library_hash or library_hash in seen_fallback_hashes:
            continue

        seen_fallback_hashes.add(library_hash)
        fallback_instances.append(
            {
                "library_hash16": library_hash,
                "library_label": token,
            }
        )

    return dedupe(thesaurus_libraries), fallback_instances

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

def paper_url(paperids: list[str]) -> list[str]:
    urls: list[str] = []
    for paperid in paperids:
        if not paperid:
            continue
        if paperid.startswith("arxiv:"):
            arxiv_id = paperid.split(":", 1)[1]
            urls.append(f"https://arxiv.org/abs/{arxiv_id}")
        elif paperid.startswith("doi:"):
            doi_id = paperid.split(":", 1)[1]
            urls.append(f"https://doi.org/{doi_id}")
        elif paperid.startswith("paperswithcode_id:"):
            pwc_id = paperid.split(":", 1)[1]
            urls.append(f"https://paperswithcode.com/dataset/{pwc_id}")
    return dedupe(urls)