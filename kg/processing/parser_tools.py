import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
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
NS_DATALENS_THESAURUS = "http://ns.inria.fr/datalens/thesaurus#"
NS_DATALENS_DATA_LIBRARY = "http://ns.inria.fr/datalens/data#library/"

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

def get_tag_with_prefix(tags: list[str], prefix: str, normalize: bool = True) -> list[str]:
    values: list[str] = []
    to_remove: list[str] = []
    # Iterate over a shallow copy to avoid skipping items when removing
    for tag in list(tags):
        if tag.startswith(prefix):
            value = tag.split(":", 1)[1]
            if normalize:
                value = normalize_string(value)
            if value:
                values.append(value)
            to_remove.append(tag)

    for tag in to_remove:
        try:
            tags.remove(tag)
        except ValueError:
            pass

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
            tags.remove(tag)
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


# -- HuggingFace helpers (shared) -------------------------------------------------
HUGGING_FACE_DATASETS_URL = re.compile(r"https?://huggingface\.co/datasets/([^\s?#/)]+(?:/[^\s?#/]+)?)", re.IGNORECASE)
HUGGING_FACE_MODELS_URL = re.compile(r"https?://huggingface\.co/(?!datasets/)([^\s?#/]+/[^\s?#/]+)", re.IGNORECASE)
HUGGING_FACE_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# Values that must remain raw and not be interpreted as HF ids
RAW_ONLY_HF_VALUES = {
    "original",
    "custom",
    "generated",
    "derived",
    "unknown",
    "none",
    "found",
    "modified",
    "curated",
    "parsed",
    "crawled",
    "third-party",
    "external",
    "internal",
    "own",
    "online",
    "localdoc",
    "personal",
    "combination",
    "n/a",
    "na",
    "other",
}


def normalize_hf_identifier(value: Any) -> str | None:
    text = normalize_string(value)
    if not text:
        return None

    # strip common decorators like 'extended/' or 'extended|'
    if text.startswith("extended/"):
        text = text[len("extended/"):]
    elif text.startswith("extended|"):
        text = text[len("extended|"):]

    # Try dataset URL first to avoid parsing '/datasets/<id>' as a model id.
    url_match = HUGGING_FACE_DATASETS_URL.search(text) or HUGGING_FACE_MODELS_URL.search(text)
    if url_match:
        text = url_match.group(1)

    return text

DATASET_IDS_PATH = Path(__file__).resolve().parent / "resources" / "datasets_ids.json"
MODEL_IDS_PATH = Path(__file__).resolve().parent / "resources" / "models_ids.json"


@lru_cache(maxsize=2)
def _load_local_ids(kind_path: Path) -> set[str]:
    try:
        with kind_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return set()

    if not isinstance(data, list):
        return set()

    return {
        normalized
        for item in data
        if isinstance(item, str)
        if (normalized := normalize_string(item))
    }


def huggingface_exists(resource_id: str, kind: str) -> bool:
    normalized_id = normalize_string(resource_id)
    if not normalized_id:
        return False

    if kind == "dataset":
        return normalized_id in _load_local_ids(DATASET_IDS_PATH)

    if kind == "model":
        return normalized_id in _load_local_ids(MODEL_IDS_PATH)

    return False

def split_hf_values(raw_values: list[str], kind: str = "dataset") -> tuple[list[str], list[str]]:
    raw_deduped = dedupe([value for value in (normalize_string(item) for item in raw_values) if value])
    hf_ids: list[str] = []
    non_hf: list[str] = []

    for raw_value in raw_deduped:
        candidate = normalize_hf_identifier(raw_value)
        if not candidate:
            continue

        if candidate.lower() in RAW_ONLY_HF_VALUES:
            continue

        if not HUGGING_FACE_ID.fullmatch(candidate):
            non_hf.append(candidate)
            continue

        if huggingface_exists(candidate, kind=kind):
            hf_ids.append(candidate)
        else:
            non_hf.append(candidate)

    return dedupe(hf_ids), dedupe(non_hf)
