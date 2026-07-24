import re
from typing import Iterable

from kg.processing.canonical_thesaurus import DATASET_LIBRARY_CANONICAL, FORMAT_CANONICAL, MODALITY_CANONICAL, MODEL_LIBRARY_CANONICAL, SIZE_CATEGORY_CANONICAL, SUBTASK_CANONICAL, TASK_CANONICAL, _canonical_lookup
from kg.processing.parser_tools import dedupe


# -------------------------
# TASK MAPPING
# -------------------------

TASK_TAGS = {
    "classification",
    "binary classification",
    "multiclass classification",
    "multilabel classification",
    "text classification",
    "image classification",
    "video classification",
    "audio classification",

    "regression",
    "linear regression",
    "logistic regression",

    "object detection",
    "segmentation",
    "image segmentation",

    "question answering",
    "retrieval question answering",

    "summarization",

    "translation",

    "text generation",
    "text-to-image",
    "image-to-text",

    "speech-to-text",
    "text-to-speech",
    "automatic speech recognition",

    "clustering",

    "forecasting",
}


TASK_ALIASES = {
    "nlp": "text",
    "natural language processing": "text",

    "sentiment analysis": "text classification",

    "forecast": "time series analysis",

    "object recognition": "object detection",

    "image recognition": "image classification",
}


def extract_tasks(tags: Iterable[str]) -> list[str]:

    result = set()

    for tag in tags:

        tag = tag.lower().strip()

        if tag in TASK_TAGS:
            result.add(tag)

        if tag in TASK_ALIASES:
            result.add(TASK_ALIASES[tag])

    return sorted(result)



# -------------------------
# LANGUAGE MAPPING
# -------------------------

LANGUAGE_TAGS = {
    "english",
    "french",
    "german",
    "spanish",
    "italian",
    "portuguese",
    "japanese",
    "chinese",
    "korean",
    "arabic",
    "hindi",
    "russian",
    "dutch",
    "polish",
    "turkish",
    "vietnamese",
    "thai",
    "indonesian",
    "multilingual",
}


LANGUAGE_CODES = {
    "english": "en",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "japanese": "ja",
    "chinese": "zh",
    "korean": "ko",
    "arabic": "ar",
    "hindi": "hi",
    "russian": "ru",
}


def extract_languages(tags: Iterable[str]) -> list[str]:

    result = []

    for tag in tags:

        tag = tag.lower().strip()

        if tag in LANGUAGE_TAGS:
            result.append(tag)

    return sorted(set(result))



# -------------------------
# REGION MAPPING
# -------------------------

REGION_PARENT = {

    "japan": "asia",
    "china": "asia",
    "india": "asia",
    "korea": "asia",
    "russia": "asia",

    "france": "europe",
    "germany": "europe",
    "italy": "europe",
    "spain": "europe",
    "uk": "europe",

    "canada": "north america",
    "united states": "north america",
    "mexico": "north america",

    "brazil": "south america",

    "australia": "oceania",
    "greenland": "north america",
}


REGION_TAGS = {

    "global",

    "asia",
    "europe",
    "africa",
    "oceania",

    "north america",
    "south america",

    "antarctica",

    "japan",
    "china",
    "india",
    "korea",
    "russia",

    "united states",
    "canada",
    "mexico",

    "brazil",
    "australia",
    "greenland",
}

CANONICALS = {
    "modality": MODALITY_CANONICAL,
    "format": FORMAT_CANONICAL,
    "size_category": SIZE_CATEGORY_CANONICAL,
    "dataset_library": DATASET_LIBRARY_CANONICAL,
    "model_library": MODEL_LIBRARY_CANONICAL,
    "task": TASK_CANONICAL,
    "subtask": SUBTASK_CANONICAL,
    "other": None,
}


def extract_regions(tags: Iterable[str]) -> list[str]:

    result = set()

    for tag in tags:

        tag = tag.lower().strip()

        if tag in REGION_TAGS:

            result.add(tag)

            if tag in REGION_PARENT:
                result.add(
                    REGION_PARENT[tag]
                )

    return sorted(result)



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

def canonicalize(values: list[str], canonical: str | None = None) -> list[str]:
    output: list[str] = []
    if CANONICALS.get(canonical) is None:
        for value in values:
            canonical_localname = make_unique_local_name(value, set(output))
            if not canonical_localname:
                continue
            output.append(canonical_localname)
    else:
        for value in values:
            canonical_localname = _canonical_lookup(value, canonical)
            if not canonical_localname:
                continue
            output.append(canonical_localname)

    return dedupe(output)