import argparse
import os
import re
from typing import Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _first_existing_path(candidates: List[str]) -> str:
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


DEFAULT_MISSING_PATH = _first_existing_path(
    [
        os.path.join(SCRIPT_DIR, "datasets_new_0.txt"),
        os.path.join(SCRIPT_DIR, "..", "datasets_new_0.txt"),
    ]
)
DEFAULT_RELATIONS_PATH = _first_existing_path(
    [
        os.path.join(SCRIPT_DIR, "datasets_new_ids_to_category.txt"),
        os.path.join(SCRIPT_DIR, "..", "datasets_new_ids_to_category.txt"),
        os.path.join(SCRIPT_DIR, "..", "task_stats", "datasets_new_ids_to_category.txt"),
    ]
)
DEFAULT_IDS_IDS_RELATIONS_PATH = _first_existing_path(
    [
        os.path.join(SCRIPT_DIR, "datasets_new_ids_to_ids.txt"),
        os.path.join(SCRIPT_DIR, "..", "datasets_new_ids_to_ids.txt"),
        os.path.join(SCRIPT_DIR, "..", "task_stats", "datasets_new_ids_to_ids.txt"),
    ]
)
DEFAULT_OUTPUT_PATH = os.path.join(SCRIPT_DIR, "tasks_missing_broader_proposals.txt")


def parse_missing_task_ids(path: str) -> List[Tuple[str, int]]:
    with open(path, "r", encoding="utf-8") as file:
        lines = [line.rstrip("\n") for line in file]

    in_task_ids_section = False
    in_not_found = False
    tasks: List[Tuple[str, int]] = []

    for line in lines:
        stripped = line.strip()

        if stripped == "TASK IDS -> MLUO THESAURUS:":
            in_task_ids_section = True
            in_not_found = False
            continue

        if not in_task_ids_section:
            continue

        if stripped == "NOT_FOUND:":
            in_not_found = True
            continue

        if in_not_found:
            if not stripped:
                continue
            if stripped.endswith(":"):
                break
            if ":" not in stripped:
                continue

            task_id, raw_count = stripped.split(":", 1)
            task_id = task_id.strip()
            count_match = re.search(r"\d+", raw_count)
            count = int(count_match.group(0)) if count_match else 0
            if task_id:
                tasks.append((task_id, count))

    return tasks


def parse_directional_relations(path: str) -> Dict[str, List[Tuple[str, int, float]]]:
    with open(path, "r", encoding="utf-8") as file:
        lines = [line.rstrip("\n") for line in file]

    current_task = None
    relations: Dict[str, List[Tuple[str, int, float]]] = {}

    header_pattern = re.compile(r"^([a-z0-9\-]+)\s*\((\d+)\s+datasets\):\s*$")
    relation_pattern = re.compile(
        r"^\s*([a-z0-9\-]+):\s*(\d+)\s*\(([0-9]+(?:\.[0-9]+)?)%\)\s*\|\s*reverse:\s*([0-9]+(?:\.[0-9]+)?)%\s*$"
    )

    for line in lines:
        header_match = header_pattern.match(line.strip())
        if header_match:
            current_task = header_match.group(1)
            relations.setdefault(current_task, [])
            continue

        if current_task is None:
            continue

        relation_match = relation_pattern.match(line)
        if relation_match:
            category = relation_match.group(1)
            count = int(relation_match.group(2))
            percentage = float(relation_match.group(3))
            relations[current_task].append((category, count, percentage))

    return relations


def parse_id_to_category_relations(path: str) -> Dict[str, List[Tuple[str, int, float]]]:
    return parse_directional_relations(path)


def parse_id_to_id_relations(path: str) -> Dict[str, List[Tuple[str, int, float]]]:
    return parse_directional_relations(path)


def select_broader(relations: List[Tuple[str, int, float]]) -> List[Tuple[str, int, float, str]]:
    if not relations:
        return []

    above_90 = [item for item in relations if item[2] > 90.0]
    if above_90:
        return [(cat, count, pct, "pct>90") for cat, count, pct in above_90]

    best = max(relations, key=lambda item: (item[2], item[1], item[0]))
    if best[2] > 80.0:
        return [(best[0], best[1], best[2], "best_pct>80")]

    return []


def write_output(
    output_path: str,
    missing_tasks: List[Tuple[str, int]],
    id_to_cat_relations: Dict[str, List[Tuple[str, int, float]]],
    id_to_id_relations: Dict[str, List[Tuple[str, int, float]]],
) -> Tuple[int, int, int, int]:
    with_broader = []
    without_broader = []

    for task_id, dataset_count in missing_tasks:
        chosen = select_broader(id_to_cat_relations.get(task_id, []))
        if chosen:
            with_broader.append((task_id, dataset_count, chosen))
        else:
            without_broader.append((task_id, dataset_count))

    with_ids_fallback = []
    without_ids_fallback = []
    for task_id, dataset_count in without_broader:
        chosen_ids = select_broader(id_to_id_relations.get(task_id, []))
        if chosen_ids:
            with_ids_fallback.append((task_id, dataset_count, chosen_ids))
        else:
            without_ids_fallback.append((task_id, dataset_count))

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("MISSING TASK IDS -> BROADER PROPOSALS\n")
        file.write("Rules: use all categories with pct > 90%; if none, use top category only if pct > 80%.\n\n")
        file.write(f"COUNT_TOTAL: {len(missing_tasks)}\n")
        file.write(f"COUNT_WITH_BROADER: {len(with_broader)}\n")
        file.write(f"COUNT_WITHOUT_BROADER: {len(without_broader)}\n\n")

        file.write("WITH_BROADER:\n\n")
        for task_id, dataset_count, chosen in with_broader:
            file.write(f"{task_id}: ({task_id.replace('-', ' ').title()}) | datasets={dataset_count}\n")
            for category, relation_count, pct, rule in sorted(chosen, key=lambda item: (-item[2], -item[1], item[0])):
                file.write(
                    f"  - {category} | pct={pct:.2f}% | pair_count={relation_count} | rule={rule}\n"
                )
            file.write("\n")

        file.write("WITHOUT_BROADER:\n\n")
        for task_id, dataset_count in without_broader:
            file.write(f"{task_id}: ({task_id.replace('-', ' ').title()}) | datasets={dataset_count}\n")
            file.write("  - NO_BROADER_CANDIDATE\n\n")

        file.write("---\n\n")
        file.write("ADDITIONAL_CANDIDATES_FROM_TASK_ID_TO_TASK_ID (on WITHOUT_BROADER):\n\n")
        file.write(f"COUNT_WITH_IDS_FALLBACK: {len(with_ids_fallback)}\n")
        file.write(f"COUNT_WITHOUT_IDS_FALLBACK: {len(without_ids_fallback)}\n\n")

        file.write("WITH_IDS_FALLBACK:\n\n")
        for task_id, dataset_count, chosen_ids in with_ids_fallback:
            file.write(f"{task_id}: ({task_id.replace('-', ' ').title()}) | datasets={dataset_count}\n")
            for related_task, relation_count, pct, rule in sorted(
                chosen_ids, key=lambda item: (-item[2], -item[1], item[0])
            ):
                file.write(
                    f"  - {related_task} | pct={pct:.2f}% | pair_count={relation_count} | rule={rule}\n"
                )
            file.write("\n")

        file.write("WITHOUT_IDS_FALLBACK:\n\n")
        for task_id, dataset_count in without_ids_fallback:
            file.write(f"{task_id}: ({task_id.replace('-', ' ').title()}) | datasets={dataset_count}\n")
            file.write("  - NO_IDS_TO_IDS_CANDIDATE\n\n")

    return len(with_broader), len(without_broader), len(with_ids_fallback), len(without_ids_fallback)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ajoute des propositions de broader pour les tâches manquantes depuis datasets_new_0.txt "
            "en utilisant datasets_new_ids_to_category.txt"
        )
    )
    parser.add_argument("--missing", default=DEFAULT_MISSING_PATH, help="Fichier source avec tâches manquantes")
    parser.add_argument("--relations", default=DEFAULT_RELATIONS_PATH, help="Fichier TASK ID -> TASK CATEGORY")
    parser.add_argument(
        "--ids-relations",
        default=DEFAULT_IDS_IDS_RELATIONS_PATH,
        help="Fichier TASK ID -> TASK ID",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Fichier de sortie")
    args = parser.parse_args()

    missing_tasks = parse_missing_task_ids(args.missing)
    id_to_cat_relations = parse_id_to_category_relations(args.relations)
    id_to_id_relations = parse_id_to_id_relations(args.ids_relations)
    with_broader_count, without_broader_count, with_ids_fallback_count, without_ids_fallback_count = write_output(
        args.output,
        missing_tasks,
        id_to_cat_relations,
        id_to_id_relations,
    )

    print(f"Tâches manquantes traitées: {len(missing_tasks)}")
    print(f"Avec broader: {with_broader_count}")
    print(f"Sans broader: {without_broader_count}")
    print(f"Sans broader mais avec fallback ids_to_ids: {with_ids_fallback_count}")
    print(f"Sans broader et sans fallback ids_to_ids: {without_ids_fallback_count}")
    print(f"Sortie écrite: {args.output}")


if __name__ == "__main__":
    main()
