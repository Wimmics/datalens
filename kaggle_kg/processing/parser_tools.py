import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

MULTI_SPACE = re.compile(r"\s+")

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


def normalize_url(value: Any) -> str | None:
    text = normalize_string(value)
    if not text:
        return None
    return quote(text, safe="/-_.~")


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

def extract_unique_tag(tags: list[str], tag: str) -> bool | None:
    if tag in tags:
        tags.remove(tag)
        return True
    return False

# Resource existence checks

HUGGING_FACE_DATASETS_URL = re.compile(r"https?://huggingface\.co/datasets/([^\s?#/)]+(?:/[^\s?#/]+)?)", re.IGNORECASE)
HUGGING_FACE_MODELS_URL = re.compile(r"https?://huggingface\.co/(?!datasets/)([^\s?#/]+/[^\s?#/]+)", re.IGNORECASE)
HUGGING_FACE_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
DATASET_IDS_PATH = Path(__file__).resolve().parent / "resources" / "dataset_ids.json"
MODEL_IDS_PATH = Path(__file__).resolve().parent / "resources" / "model_ids.json"

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

# External URIs

from functools import cache
import requests
import pycountry

LANGUAGE_2 = re.compile(r"^[a-z]{2}$")
LANGUAGE_3 = re.compile(r"^[a-z]{3}$")
LANGUAGE_BCP47 = re.compile(r"^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$")
REGION_ALPHA2 = re.compile(r"^[a-z]{2}$")

SPDX_CANONICAL_IDS = {
    # Hugging Face
    "apache-2.0": "Apache-2.0",
    "afl-3.0": "AFL-3.0",
    "agpl-3.0": "AGPL-3.0-only",
    "artistic-2.0": "Artistic-2.0",
    "bsl-1.0": "BSL-1.0",
    "bsd": "BSD-2-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-3-clause-clear": "BSD-3-Clause",
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

    # Kaggle
    "Apache 2.0": "Apache-2.0",
    "MIT": "MIT",
    "GPL 2": "GPL-2.0-only",
    "GPL 3": "GPL-3.0-only",
    "GNU Affero General Public License 3.0": "AGPL-3.0-only",
    "GNU Lesser General Public License 3.0": "LGPL-3.0-only",
    "GNU Free Documentation License 1.3": "GFDL-1.3-or-later",
    "BSD-3-Clause": "BSD-3-Clause",
    "ODC Attribution License (ODC-By)": "ODC-By-1.0",
    "ODC Public Domain Dedication and Licence (PDDL)": "PDDL-1.0",
    "Community Data License Agreement - Permissive - Version 1.0": "CDLA-Permissive-1.0",
    "Community Data License Agreement - Sharing - Version 1.0": "CDLA-Sharing-1.0",
}

CC_LICENSE_URIS = {
    # Hugging Face
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

    # Kaggle
    "CC0: Public Domain":
        "https://creativecommons.org/publicdomain/zero/1.0/",

    "Attribution 4.0 International (CC BY 4.0)":
        "https://creativecommons.org/licenses/by/4.0/",

    "CC BY-SA 4.0":
        "https://creativecommons.org/licenses/by-sa/4.0/",

    "CC BY-SA 3.0":
        "https://creativecommons.org/licenses/by-sa/3.0/",

    "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)":
        "https://creativecommons.org/licenses/by-nc/4.0/",

    "Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)":
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",

    "Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)":
        "https://creativecommons.org/licenses/by-nd/4.0/",

    "Attribution 3.0 Unported (CC BY 3.0)":
        "https://creativecommons.org/licenses/by/3.0/",
}

OTHER_LICENSE_URIS = {
    # Kaggle
    "Llama 2 Community License":
        "https://ai.meta.com/llama/license/",

    "Llama 3 Community License":
        "https://www.llama.com/llama3/license/",

    "Llama 3.1 Community License":
        "https://www.llama.com/llama3_1/license/",

    "Llama 3.2 Community License":
        "https://www.llama.com/llama3_2/license/",

    "Llama 3.2 (Vision) Community License":
        "https://www.llama.com/llama3_2/license/",

    "Llama 3.3 Community License":
        "https://www.llama.com/llama3_3/license/",

    "Gemma":
        "https://ai.google.dev/gemma/terms",

    "BigScience Open RAIL-M License":
        "https://huggingface.co/spaces/bigscience/license",

    "AI Pubs Open RAIL-M License":
        "https://huggingface.co/spaces/AIpubs/Open-RAIL-M",

    "AI Pubs Research-Use RAIL-M License":
        "https://huggingface.co/spaces/AIpubs/Research-RAIL-M",

    "World Bank Dataset Terms of Use":
        "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",

    "EU ODP Legal Notice":
        "https://data.europa.eu/eli/reg_impl/2023/138/oj",

    "Reddit API Terms":
        "https://www.redditinc.com/policies/data-api-terms",

    "U.S. Government Works":
        "https://www.usa.gov/government-works",

    "Database: Open Database, Contents: © Original Authors":
        None,

    "Database: Open Database, Contents: Database Contents":
        None,

    "Data files © Original Authors":
        None,

    "RAIL (specified in description)":
        None,
}

CONTINENTS = {
    "af": "6255146",  # Africa
    "as": "6255147",  # Asia
    "eu": "6255148",  # Europe
    "na": "6255149",  # North America
    "sa": "6255150",  # South America
    "oc": "6255151",  # Oceania
    "an": "6255152",  # Antarctica
}

REGION_TAGS = {
    # Continents
    "africa": "af",
    "antarctica": "an",
    "asia": "as",
    "europe": "eu",
    "north america": "na",
    "south america": "sa",
    "oceania": "oc",

    # Pays
    "australia": "au",
    "brazil": "br",
    "canada": "ca",
    "china": "cn",
    "greenland": "gl",
    "india": "in",
    "japan": "jp",
    "mexico": "mx",
    "russia": "ru",
    "united states": "us",

    # Régions non ISO / non GeoNames countryInfo
    "global": None,
    "korea": None,
    "middle east": None,
}

AMBIGUOUS_LANGUAGE_TAGS = {
    "eu",   # Europe / basque
    "id",   # identifier / indonesian
}

NS_LEXVO_ISO639_1 = "https://lexvo.org/id/iso639-1/"
NS_LEXVO_ISO639_3 = "https://lexvo.org/id/iso639-3/"
NS_SPDX_LICENSES = "https://spdx.org/licenses/"
NS_GEONAMES = "http://sws.geonames.org/"


@cache
def iso639_1_codes() -> set[str]:
    return {
        lang.alpha_2.lower()
        for lang in pycountry.languages
        if hasattr(lang, "alpha_2")
    }

@cache
def iso639_3_codes() -> set[str]:
    return {
        lang.alpha_3.lower()
        for lang in pycountry.languages
        if hasattr(lang, "alpha_3")
    }

@cache
def geonames_codes() -> dict[str, str]:
    mapping: dict[str, str] = {}

    # Pays (ISO)
    url = (
        "https://download.geonames.org/export/dump/"
        "countryInfo.txt"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    for line in response.text.splitlines():
        if not line or line.startswith("#"):
            continue

        cols = line.split("\t")

        if len(cols) <= 16:
            continue

        iso = cols[0].strip().lower()
        geoname_id = cols[16].strip()

        if iso and geoname_id:
            mapping[iso] = (
                f"{NS_GEONAMES}{geoname_id}/"
            )

    # Continents (GeoNames)
    for name, geoname_id in CONTINENTS.items():
        mapping[name] = (
            f"{NS_GEONAMES}{geoname_id}/"
        )

    return mapping


@cache
def language_tags() -> dict[str, str]:
    mapping: dict[str, str] = {}

    for lang in pycountry.languages:
        if not hasattr(lang, "name"):
            continue

        code = getattr(lang, "alpha_2", None) or getattr(lang, "alpha_3", None)
        if not code:
            continue

        key = (
            lang.name.lower()
            .replace(", ", "-")
            .replace(",", "-")
            .replace(" ", "-")
        )

        mapping[key] = code.lower()

    # Synonymes fréquents (Kaggle/HuggingFace)
    mapping.update({
        "castilian": "es",
        "flemish": "nl",
        "greenlandic": "kl",
        "kalaallisut": "kl",
        "maldivian": "dv",
        "divehi": "dv",
        "moldavian": "ro",
        "moldovan": "ro",
        "kirghiz": "ky",
        "kyrgyz": "ky",
        "kwanyama": "kj",
        "kuanyama": "kj",
        "gaelic": "gd",
        "scottish-gaelic": "gd",
        "church-slavic": "cu",
        "old-bulgarian": "cu",
        "chichewa": "ny",
        "chewa": "ny",
        "nyanja": "ny",
        "chuang": "za",
        "zhuang": "za",
        "uighur": "ug",
        "uyghur": "ug",
        "pashto-pushto": "ps",
        "sinhalese": "si",
        "central-khmer": "km",
        "nuosu": "iii",
        "norwegian-bokmål": "nb",
        "norwegian-nynorsk": "nn",
        "interlingue-occidental": "ie",
        "valencian": "ca",
        "multilingual": None,
    })

    return mapping

def get_tag_alone(tags: list[str], kind) -> list[str]:
    tokens: list[str] = []

    if kind == "language":
        test = (iso639_1_codes() | iso639_3_codes()) - AMBIGUOUS_LANGUAGE_TAGS
    elif kind == "license":
        test = SPDX_CANONICAL_IDS.keys() | CC_LICENSE_URIS.keys()
    else:
        raise ValueError(f"Unsupported kind: {kind}")

    for tag in tags:
        if ":" in tag:
            continue
        candidate = tag.lower().replace("_", "-")
        if candidate in test:
            tokens.append(candidate)
    
    tags[:] = [tag for tag in tags if tag.lower().replace("_", "-") not in tokens]
    return dedupe(tokens)


def region_uri(token: str) -> str | None:
    return geonames_codes().get(
        REGION_TAGS.get(token.strip().lower())
    )


# def language_uri(token: str) -> str | None:
#     token = token.strip().lower().replace("_", "-")

#     if not LANGUAGE_BCP47.fullmatch(token):
#         return None

#     primary = token.split("-", 1)[0]

#     if len(primary) == 2 and primary in iso639_1_codes():
#         return f"{NS_LEXVO_ISO639_1}{primary}"

#     if len(primary) == 3 and primary in iso639_3_codes():
#         return f"{NS_LEXVO_ISO639_3}{primary}"

#     return None

def language_uri(tag: str) -> str | None:
    code = language_tags().get(tag.lower())
    if not code:
        return None

    if code in iso639_1_codes():
        return f"{NS_LEXVO_ISO639_1}{code}"

    if code in iso639_3_codes():
        return f"{NS_LEXVO_ISO639_3}{code}"

    return None


def license_uri(token: str) -> str | None:
    # token = token.strip().lower()

    if token in {"unknown", "other"}:
        return None

    if token in CC_LICENSE_URIS:
        return CC_LICENSE_URIS[token]

    if token in OTHER_LICENSE_URIS:
        return OTHER_LICENSE_URIS[token]

    spdx_id = SPDX_CANONICAL_IDS.get(token)

    if spdx_id:
        return f"{NS_SPDX_LICENSES}{spdx_id}"

    return None


def build_uris(values: list[str], kind: str) -> list[str]:
    builders = {
        "language": language_uri,
        "region": region_uri,
        "license": license_uri,
    }

    builder = builders.get(kind)

    if builder is None:
        raise ValueError(f"Unsupported kind: {kind}")

    uris = [
        uri
        for value in values
        if (uri := builder(value)) is not None
    ]

    return dedupe(uris)

