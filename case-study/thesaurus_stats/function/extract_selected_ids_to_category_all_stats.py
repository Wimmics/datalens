import argparse
import os
from typing import List

from extract_tasks import _compute_relation_stats, extract_task_records


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JSON_PATH = os.path.join(SCRIPT_DIR, "..", "datasets_new.json")
DEFAULT_SELECTION_PATH = os.path.join(SCRIPT_DIR, "tasks_missing_broader_proposals.txt")
DEFAULT_OUTPUT_PATH = os.path.join(SCRIPT_DIR, "datasets_new_selected_ids_to_category_all_stats.txt")


def parse_selected_tasks(
    selection_path: str,
    main_section: str = "ADDITIONAL_CANDIDATES_FROM_TASK_ID_TO_TASK_ID (on WITHOUT_BROADER):",
    subsection: str = "WITHOUT_IDS_FALLBACK:",
) -> List[str]:
    with open(selection_path, "r", encoding="utf-8") as file:
        lines = [line.rstrip("\n") for line in file]

    in_main_section = False
    in_subsection = False
    tasks = []

    for line in lines:
        stripped = line.strip()

        if not in_main_section:
            if stripped == main_section:
                in_main_section = True
            continue

        if in_main_section and stripped.endswith(":") and stripped != subsection and stripped != main_section:
            in_subsection = False

        if stripped == subsection:
            in_subsection = True
            continue

        if in_subsection:
            if not stripped:
                continue
            if stripped.endswith(":"):
                break
            if ":" not in stripped:
                continue
            task = stripped.split(":", 1)[0].strip()
            if task:
                tasks.append(task)

    return tasks


def write_id_to_category_all_stats(output_path: str, stats: dict, selected_ids: List[str]) -> None:
    id_to_cat = stats["id_to_cat"]
    cat_to_id = stats["cat_to_id"]
    id_counts = stats["id_dataset_counts"]
    cat_counts = stats["cat_dataset_counts"]

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("TASK ID -> TASK CATEGORY (ALL STATS, NO THRESHOLD):\n")

        if not selected_ids:
            file.write("Aucune task sélectionnée.\n")
            return

        for task_id in selected_ids:
            source_count = id_counts.get(task_id, 0)
            file.write(f"\n{task_id} ({source_count} datasets):\n")

            related = [
                (category, count)
                for (source, category), count in id_to_cat.items()
                if source == task_id
            ]
            related.sort(key=lambda item: (-item[1], item[0]))

            if not related:
                file.write("  (aucune catégorie liée)\n")
                continue

            for category, count in related:
                percentage = (count / source_count) * 100 if source_count else 0
                reverse_source_count = cat_counts.get(category, 0)
                reverse_count = cat_to_id.get((category, task_id), 0)
                reverse_percentage = (reverse_count / reverse_source_count) * 100 if reverse_source_count else 0
                file.write(
                    f"  {category}: {count} ({percentage:.2f}%) | reverse: {reverse_percentage:.2f}%\n"
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère les stats TASK ID -> TASK CATEGORY pour des tasks sélectionnées, sans seuil."
    )
    parser.add_argument("--json", default=DEFAULT_JSON_PATH, help="Chemin du JSON source")
    parser.add_argument(
        "--selection",
        default=DEFAULT_SELECTION_PATH,
        help="Chemin du fichier texte contenant la section des tasks sélectionnées",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Chemin du fichier de sortie")
    args = parser.parse_args()

    records = extract_task_records(args.json)
    if not records:
        raise RuntimeError(f"Aucune donnée extraite depuis: {args.json}")

    selected_ids = parse_selected_tasks(args.selection)
    stats = _compute_relation_stats(records)
    write_id_to_category_all_stats(args.output, stats, selected_ids)

    print(f"Tasks sélectionnées: {len(selected_ids)}")
    print(f"Sortie écrite: {args.output}")


if __name__ == "__main__":
    main()
