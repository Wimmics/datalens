import argparse
import os
import re
from collections import defaultdict, deque

from rdflib import Graph, Namespace
from rdflib.namespace import SKOS


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_THESAURUS_PATH = os.path.join(SCRIPT_DIR, "mluo_thesaurus.ttl")
DEFAULT_STATS_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "datasets_new_1.txt")
)
DEFAULT_CATEGORY_OUTPUT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "task_categories_parents.txt")
)
DEFAULT_TASK_OUTPUT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "tasks_parents.txt")
)

MLUO_TH = Namespace("http://example.org/mluo/thesaurus#")


def _local_name(node):
    text = str(node)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    if "/" in text:
        return text.rsplit("/", 1)[-1]
    return text


def _pref_label(graph, node):
    for label in graph.objects(node, SKOS.prefLabel):
        return str(label)
    return _local_name(node)


def _build_broader_index(graph):
    broader_index = defaultdict(set)
    for child, parent in graph.subject_objects(SKOS.broader):
        broader_index[child].add(parent)
    return broader_index


def _ancestors_with_distance(node, broader_index):
    distances = {}
    queue = deque([(node, 0)])
    seen = {node}

    while queue:
        current, depth = queue.popleft()
        for parent in broader_index.get(current, set()):
            next_depth = depth + 1
            if parent not in distances or next_depth < distances[parent]:
                distances[parent] = next_depth
            if parent not in seen:
                seen.add(parent)
                queue.append((parent, next_depth))

    return distances


def _parse_items_from_block(lines, header):
    in_block = False
    names = []

    for line in lines:
        stripped = line.strip()

        if stripped == header:
            in_block = True
            continue

        if in_block and stripped.endswith("-> MLUO THESAURUS:") and stripped != header:
            break

        if not in_block or not stripped:
            continue

        if stripped.endswith(":"):
            continue
        if stripped in {
            "---",
            "SUMMARY:",
            "FOUND:",
            "NOT_IN_HIERARCHY:",
            "IN_HIERARCHY_NOT_REACHING_TOPCONCEPT:",
            "NOT_FOUND:",
        }:
            continue

        match = re.match(r"^([a-z0-9\-]+):\s+\d+", stripped)
        if match:
            names.append(match.group(1))

    unique_ordered_names = []
    seen = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            unique_ordered_names.append(name)
    return unique_ordered_names


def _load_requested_names(stats_path):
    with open(stats_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    category_names = _parse_items_from_block(lines, "TASK CATEGORIES -> MLUO THESAURUS:")
    task_names = _parse_items_from_block(lines, "TASK IDS -> MLUO THESAURUS:")
    return category_names, task_names


def _build_local_name_index(graph):
    index = {}
    for concept in graph.subjects(SKOS.inScheme, MLUO_TH.TaskScheme):
        index[_local_name(concept)] = concept
    return index


def _write_parent_report(graph, concept_names, concept_index, broader_index, output_path, title):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write(f"COUNT: {len(concept_names)}\n\n")

        for subject_name in concept_names:
            subject = concept_index.get(subject_name)
            f.write(f"{subject_name}:")
            if subject is None:
                f.write("\n  - NOT_FOUND_IN_THESAURUS\n\n")
                continue

            subject_label = _pref_label(graph, subject)
            distances = _ancestors_with_distance(subject, broader_index)

            f.write(f" ({subject_label}):\n")
            if not distances:
                f.write("  - NO_PARENT\n\n")
                continue

            ordered_parents = sorted(
                distances.items(),
                key=lambda item: (item[1], _local_name(item[0])),
            )

            for parent, depth in ordered_parents:
                parent_name = _local_name(parent)
                parent_label = _pref_label(graph, parent)
                f.write(f"  - {parent_name} ({parent_label}) | distance={depth}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Export all parent concepts (transitive skos:broader) for task categories "
            "and tasks from mluo_thesaurus.ttl into two separate files."
        )
    )
    parser.add_argument("--thesaurus", default=DEFAULT_THESAURUS_PATH, help="Path to mluo_thesaurus.ttl")
    parser.add_argument(
        "--stats",
        default=DEFAULT_STATS_PATH,
        help="Path to datasets_new_1.txt containing TASK CATEGORIES and TASK IDS sections",
    )
    parser.add_argument(
        "--categories-output",
        default=DEFAULT_CATEGORY_OUTPUT_PATH,
        help="Output path for task categories parents report",
    )
    parser.add_argument(
        "--tasks-output",
        default=DEFAULT_TASK_OUTPUT_PATH,
        help="Output path for tasks parents report",
    )
    args = parser.parse_args()

    if not os.path.exists(args.thesaurus):
        raise FileNotFoundError(f"Thesaurus not found: {args.thesaurus}")
    if not os.path.exists(args.stats):
        raise FileNotFoundError(f"Stats file not found: {args.stats}")

    graph = Graph()
    graph.parse(args.thesaurus, format="turtle")

    task_categories, tasks = _load_requested_names(args.stats)
    concept_index = _build_local_name_index(graph)
    broader_index = _build_broader_index(graph)

    _write_parent_report(
        graph,
        task_categories,
        concept_index,
        broader_index,
        args.categories_output,
        "TASK CATEGORIES -> ALL PARENTS",
    )
    _write_parent_report(
        graph,
        tasks,
        concept_index,
        broader_index,
        args.tasks_output,
        "TASKS -> ALL PARENTS",
    )

    print(f"Task categories parents written to: {args.categories_output}")
    print(f"Tasks parents written to: {args.tasks_output}")


if __name__ == "__main__":
    main()