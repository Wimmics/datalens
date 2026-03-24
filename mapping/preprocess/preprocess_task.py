"""
Preprocessing script: enrichit task_categories.json avec les subType issus de
task_categories_model.json et task_categories_dataset.json, et ajoute les tâches
présentes dans ces deux sources mais absentes de la base.

Résultat : tasks_enriched.json (task_categories + task_ids) dans le même répertoire.

Logique de correspondance :
  - model  : pipeline_tag[*].id      == clé dans task_categories.json
  - dataset: task_categories[*].label == clé dans task_categories.json
             (les labels dataset sont des slugs minuscules, identiques aux clés)
"""

import json
from pathlib import Path


ABBREVIATIONS = {"3d", "2d", "ml", "qa", "nlp", "asr", "vqa", "cv", "rl"}

SOURCE_BASE      = "https://huggingface.co/api/tasks"
SOURCE_MODEL     = "https://huggingface.co/api/models-tags-by-type?type=pipeline_tag"
SOURCE_DATASET   = "https://huggingface.co/api/datasets-tags-by-type?type=task_categories"
SOURCE_TASK_IDS  = "https://huggingface.co/api/datasets-tags-by-type?type=task_ids"

SUBTYPE_LABELS = {
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "rl": "Reinforcement Learning",
    "audio": "Audio",
    "tabular": "Tabular",
    "multimodal": "Multimodal",
    "other": "Other",
}

SUBTYPE_IDS_BY_LABEL = {label.lower(): subtype_id for subtype_id, label in SUBTYPE_LABELS.items()}


def slug_to_label(slug: str) -> str:
    """
    Convertit un slug en label lisible.
    - 'tabular-to-text'           → 'Tabular-to-Text'
    - 'time-series-forecasting'   → 'Time Series Forecasting'
    - 'multiple-choice'           → 'Multiple Choice'
    - 'text-to-3d'                → 'Text-to-3D'
    """
    parts = slug.split("-")
    result: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        # "to" au milieu du slug → connecteur hyphenné (X-to-Y)
        if part.lower() == "to" and 0 < i < len(parts) - 1:
            next_part = parts[i + 1]
            capitalized_next = next_part.upper() if next_part.lower() in ABBREVIATIONS else next_part.capitalize()
            result[-1] = f"{result[-1]}-to-{capitalized_next}"
            i += 2
        else:
            result.append(part.upper() if part.lower() in ABBREVIATIONS else part.capitalize())
            i += 1
    return " ".join(result)


def format_subtype(subtype: str) -> str:
    return SUBTYPE_LABELS.get(subtype.lower(), slug_to_label(subtype))


def subtype_id(subtype: str) -> str:
    normalized = subtype.strip().lower()
    if normalized in SUBTYPE_LABELS:
        return normalized
    if normalized in SUBTYPE_IDS_BY_LABEL:
        return SUBTYPE_IDS_BY_LABEL[normalized]
    return normalized.replace(" ", "-")


def format_pref_label(value: str) -> str:
    normalized = value.strip()
    if "-" in normalized:
        return slug_to_label(normalized)
    return normalized


def preprocess(
    base_path: Path,
    model_path: Path,
    dataset_path: Path,
    task_ids_path: Path,
    output_path: Path,
) -> None:
    # --- Chargement des sources ---
    with open(base_path, encoding="utf-8") as f:
        base: dict = json.load(f)
    with open(model_path, encoding="utf-8") as f:
        model_data: dict = json.load(f)
    with open(dataset_path, encoding="utf-8") as f:
        dataset_data: dict = json.load(f)
    with open(task_ids_path, encoding="utf-8") as f:
        task_ids_data: dict = json.load(f)

    # --- Tables de correspondance ---
    # model  : id (slug) → entrée complète
    model_by_id: dict = {item["id"]: item for item in model_data["pipeline_tag"]}

    # dataset: label (slug) → entrée complète
    # Note : les labels dataset sont identiques aux clés de base (slugs minuscules)
    dataset_by_label: dict = {item["label"]: item for item in dataset_data["task_categories"]}

    result_task_categories: dict = {}

    # --- Enrichissement des entrées de base ---
    for key, task in base.items():
        enriched = dict(task)

        if "subType" not in enriched:
            if key in model_by_id:
                raw_subtype = model_by_id[key]["subType"]
                enriched["subTypeId"] = subtype_id(raw_subtype)
                enriched["subType"] = format_subtype(raw_subtype)
            elif key in dataset_by_label:
                raw_subtype = dataset_by_label[key]["subType"]
                enriched["subTypeId"] = subtype_id(raw_subtype)
                enriched["subType"] = format_subtype(raw_subtype)
            # Si non trouvé dans aucune source, on laisse sans subType
        else:
            enriched["subTypeId"] = subtype_id(enriched["subType"])
            enriched["subType"] = format_subtype(enriched["subType"])

        enriched["labelPref"] = format_pref_label(enriched.get("label", key))
        enriched["source"] = SOURCE_BASE
        result_task_categories[key] = enriched

    # --- Ajout des tâches présentes dans model mais absentes de la base ---
    added_from_model: list[str] = []
    for item in model_data["pipeline_tag"]:
        if item["id"] not in result_task_categories:
            result_task_categories[item["id"]] = {
                "id":      item["id"],
                "label":   item["label"],
                "labelPref": format_pref_label(item["label"]),
                "subTypeId": subtype_id(item["subType"]),
                "subType": format_subtype(item["subType"]),
                "type":    item["type"],
                "source":  SOURCE_MODEL,
            }
            added_from_model.append(item["id"])

    # --- Ajout des tâches présentes dans dataset mais absentes de la base et du model ---
    added_from_dataset: list[str] = []
    for item in dataset_data["task_categories"]:
        task_id = item["label"]  # le label dataset == clé/slug
        if task_id not in result_task_categories:
            # Le label fourni par dataset est un slug → on le convertit en label lisible
            label = slug_to_label(task_id)
            result_task_categories[task_id] = {
                "id":      task_id,
                "label":   label,
                "labelPref": format_pref_label(label),
                "subTypeId": subtype_id(item["subType"]),
                "subType": format_subtype(item["subType"]),
                "type":    "task_categories",
                "source":  SOURCE_DATASET,
            }
            added_from_dataset.append(task_id)

    # --- Enrichissement des task_ids (source + labelPref formaté) ---
    enriched_task_ids: list[dict] = []
    for item in task_ids_data.get("task_ids", []):
        task_id_entry = dict(item)
        task_id_entry["labelPref"] = format_pref_label(task_id_entry.get("label", ""))
        task_id_entry["source"] = SOURCE_TASK_IDS
        enriched_task_ids.append(task_id_entry)

    merged = {
        "task_categories": result_task_categories,
        "task_ids": enriched_task_ids,
    }

    # --- Écriture du résultat ---
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)

    # --- Rapport ---
    tasks_without_subtype = [k for k, v in result_task_categories.items() if "subType" not in v]
    print(f"Écrit dans : {output_path}")
    print(f"Total task_categories: {len(result_task_categories)}")
    print(f"Total task_ids       : {len(enriched_task_ids)}")
    print(f"  dont {len(base)} issues de task_categories.json (base)")
    print(f"  dont {len(added_from_model)} ajoutées depuis task_categories_model.json : {added_from_model}")
    print(f"  dont {len(added_from_dataset)} ajoutées depuis task_categories_dataset.json : {added_from_dataset}")
    if tasks_without_subtype:
        print(f"  ⚠ Tâches sans subType : {tasks_without_subtype}")


if __name__ == "__main__":
    here = Path(__file__).parent
    preprocess(
        base_path=here / "task_categories.json",
        model_path=here / "task_categories_model.json",
        dataset_path=here / "task_categories_dataset.json",
        task_ids_path=here / "task_ids.json",
        output_path=here / "tasks_enriched.json",
    )
