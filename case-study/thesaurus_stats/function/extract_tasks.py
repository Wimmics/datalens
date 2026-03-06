import json
import os
import re
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
THESAURUS_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "ontology", "mluo_thesaurus.ttl"))
MIN_DIRECTIONAL_PERCENTAGE = 75.0
JSON_FILES = [
    (
        os.path.join(SCRIPT_DIR, "datasets_new.json"),
        os.path.join(SCRIPT_DIR, "datasets_new.txt"),
    )
]


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item]
    return [value] if value else []


def _normalize_task(value):
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return normalized.strip("-")


def _compute_reaches_top_concept(concepts):
    memo = {}

    def visit(local_name, visiting):
        if local_name in memo:
            return memo[local_name]
        if local_name in visiting:
            memo[local_name] = False
            return False

        concept = concepts.get(local_name)
        if not concept:
            memo[local_name] = False
            return False
        if concept.get("has_top_concept", False):
            memo[local_name] = True
            return True

        visiting = visiting | {local_name}
        for broader_local_name in concept.get("broader_local_names", []):
            if visit(broader_local_name, visiting):
                memo[local_name] = True
                return True

        memo[local_name] = False
        return False

    for local_name in concepts:
        visit(local_name, set())

    return memo


def _build_hierarchy_paths(concepts, start_local_name, max_depth=30):
    def walk(local_name, path, depth):
        if depth > max_depth:
            return [path + ["..."]]

        concept = concepts.get(local_name)
        broader_local_names = concept.get("broader_local_names", []) if concept else []
        if not broader_local_names:
            return [path]

        paths = []
        for broader_local_name in broader_local_names:
            if broader_local_name in path:
                paths.append(path + [f"{broader_local_name} (cycle)"])
            else:
                paths.extend(walk(broader_local_name, path + [broader_local_name], depth + 1))
        return paths

    return walk(start_local_name, [start_local_name], 0)


def _format_hierarchy_paths(concepts, start_local_name):
    formatted = set()
    for path in _build_hierarchy_paths(concepts, start_local_name):
        labels = []
        for local_name in path:
            if local_name == "..." or local_name.endswith("(cycle)"):
                labels.append(local_name)
            else:
                concept = concepts.get(local_name)
                labels.append(concept.get("label", local_name) if concept else local_name)
        formatted.add(" > ".join(labels))
    return " || ".join(sorted(formatted))


def load_mluo_task_lookup(ttl_path):
    if not os.path.exists(ttl_path):
        return {}

    with open(ttl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    lookup = {}
    concepts = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:(Task|TaskCategory) ;$", line)
        if not match:
            i += 1
            continue

        local_name = match.group(1)
        pref_label = None
        has_top_concept = False
        block_lines = []

        j = i + 1
        while j < len(lines):
            block_line = lines[j].strip()
            block_lines.append(block_line)
            label_match = re.match(r'^skos:prefLabel "([^"]+)"@en ;$', block_line)
            if label_match:
                pref_label = label_match.group(1)
            if "skos:topConceptOf mluo_th:TaskScheme" in block_line:
                has_top_concept = True
            if block_line.endswith("."):
                break
            j += 1

        block_text = "\n".join(block_lines)
        broader_match = re.search(r"skos:broader\s+(.+?)\s*\.", block_text, re.DOTALL)
        broader_local_names = []
        if broader_match:
            broader_local_names = re.findall(r"mluo_th:([A-Za-z0-9\-]+)", broader_match.group(1))

        concepts[local_name] = {
            "label": pref_label or local_name,
            "has_top_concept": has_top_concept,
            "broader_local_names": sorted(set(broader_local_names)),
        }

        concept_uri = f"mluo_th:{local_name}"
        in_hierarchy = bool(broader_local_names) or has_top_concept
        for candidate in [local_name, pref_label]:
            if candidate:
                key = _normalize_task(candidate)
                lookup[key] = {
                    "uri": concept_uri,
                    "label": pref_label or local_name,
                    "in_hierarchy": in_hierarchy,
                    "local_name": local_name,
                }

        i = j + 1

    reaches_top = _compute_reaches_top_concept(concepts)
    for mapped in lookup.values():
        local_name = mapped.get("local_name")
        mapped["reaches_top_concept"] = reaches_top.get(local_name, False)
        mapped["hierarchy"] = _format_hierarchy_paths(concepts, local_name) if local_name else ""

    return lookup


def _extract_task_records(data, from_tags=False):
    records = []
    for obj in data:
        if from_tags:
            categories = []
            ids = []
            for tag in _as_list(obj.get("tags", [])):
                if not isinstance(tag, str):
                    continue
                if tag.startswith("task_categories:"):
                    categories.append(tag.split(":", 1)[1])
                elif tag.startswith("task_ids:"):
                    ids.append(tag.split(":", 1)[1])
        else:
            categories = _as_list(obj.get("task_categories"))
            ids = _as_list(obj.get("task_ids"))

        records.append({"categories": categories, "ids": ids})

    for record in records:
        record["categories"] = sorted(set(record["categories"]))
        record["ids"] = sorted(set(record["ids"]))

    return records


def extract_task_records(json_path):
    if not os.path.exists(json_path):
        print(f"Fichier introuvable : {json_path}")
        print("Veuillez vérifier le chemin du fichier JSON à analyser.")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    filename = os.path.basename(json_path).lower()
    from_tags = filename in {"datasets_new.json", "dataset_new.json", "dataset_new_extract.json"}
    return _extract_task_records(data, from_tags=from_tags)


def _build_mapping_groups(values, lookup):
    found_lines = []
    not_in_hierarchy_lines = []
    not_reaching_top_lines = []
    not_found_lines = []
    for value, count in Counter(values).most_common():
        key = _normalize_task(value)
        mapped = lookup.get(key)
        if mapped:
            if mapped.get("in_hierarchy", False) and mapped.get("reaches_top_concept", False):
                found_lines.append(f"{value}: {count}")
            elif mapped.get("in_hierarchy", False):
                hierarchy = mapped.get("hierarchy", "")
                if hierarchy:
                    not_reaching_top_lines.append(f"{value}: {count} | hierarchy: {hierarchy}")
                else:
                    not_reaching_top_lines.append(f"{value}: {count}")
            else:
                not_in_hierarchy_lines.append(f"{value}: {count}")
        else:
            not_found_lines.append(f"{value}: {count}")
    return found_lines, not_in_hierarchy_lines, not_reaching_top_lines, not_found_lines


def _compute_relation_stats(records):
    categories = []
    ids = []

    cat_dataset_counts = Counter()
    id_dataset_counts = Counter()
    cat_to_id = Counter()
    id_to_cat = Counter()
    cat_to_cat = Counter()
    id_to_id = Counter()

    for record in records:
        rec_categories = record["categories"]
        rec_ids = record["ids"]

        categories.extend(rec_categories)
        ids.extend(rec_ids)

        for cat in rec_categories:
            cat_dataset_counts[cat] += 1
        for tid in rec_ids:
            id_dataset_counts[tid] += 1

        for cat in rec_categories:
            for tid in rec_ids:
                cat_to_id[(cat, tid)] += 1
                id_to_cat[(tid, cat)] += 1

        for source in rec_categories:
            for target in rec_categories:
                if source != target:
                    cat_to_cat[(source, target)] += 1

        for source in rec_ids:
            for target in rec_ids:
                if source != target:
                    id_to_id[(source, target)] += 1

    return {
        "categories": categories,
        "ids": ids,
        "cat_dataset_counts": cat_dataset_counts,
        "id_dataset_counts": id_dataset_counts,
        "cat_to_id": cat_to_id,
        "id_to_cat": id_to_cat,
        "cat_to_cat": cat_to_cat,
        "id_to_id": id_to_id,
    }


def _write_directional_percentages(f, title, pair_counter, source_counts, reverse_pair_counter, reverse_source_counts):
    f.write(f"{title}\n")
    if not pair_counter:
        f.write("Aucune relation trouvée.\n\n")
        return

    for source, source_count in source_counts.most_common():
        related = [(target, count) for (src, target), count in pair_counter.items() if src == source]

        if not related:
            continue

        kept_related = []
        for target, count in related:
            percentage = (count / source_count) * 100 if source_count else 0
            if percentage > MIN_DIRECTIONAL_PERCENTAGE:
                reverse_source_count = reverse_source_counts.get(target, 0)
                reverse_count = reverse_pair_counter.get((target, source), 0)
                reverse_percentage = (reverse_count / reverse_source_count) * 100 if reverse_source_count else 0
                kept_related.append((target, count, percentage, reverse_percentage))

        if not kept_related:
            continue

        f.write(f"{source} ({source_count} datasets):\n")
        for target, count, percentage, reverse_percentage in sorted(kept_related, key=lambda item: (-item[1], item[0])):
            f.write(f"  {target}: {count} ({percentage:.2f}%) | reverse: {reverse_percentage:.2f}%\n")
        f.write("\n")


def _build_directional_output_paths(output_path):
    base, ext = os.path.splitext(output_path)
    if not ext:
        ext = ".txt"
    return {
        "cat_to_id": f"{base}_category_to_ids{ext}",
        "id_to_cat": f"{base}_ids_to_category{ext}",
        "cat_to_cat": f"{base}_category_to_category{ext}",
        "id_to_id": f"{base}_ids_to_ids{ext}",
    }


def write_directional_files(stats, output_path):
    paths = _build_directional_output_paths(output_path)

    with open(paths["cat_to_id"], "w", encoding="utf-8") as f:
        _write_directional_percentages(
            f,
            "TASK CATEGORY -> TASK ID:",
            stats["cat_to_id"],
            stats["cat_dataset_counts"],
            stats["id_to_cat"],
            stats["id_dataset_counts"],
        )

    with open(paths["id_to_cat"], "w", encoding="utf-8") as f:
        _write_directional_percentages(
            f,
            "TASK ID -> TASK CATEGORY:",
            stats["id_to_cat"],
            stats["id_dataset_counts"],
            stats["cat_to_id"],
            stats["cat_dataset_counts"],
        )

    with open(paths["cat_to_cat"], "w", encoding="utf-8") as f:
        _write_directional_percentages(
            f,
            "TASK CATEGORY -> TASK CATEGORY:",
            stats["cat_to_cat"],
            stats["cat_dataset_counts"],
            stats["cat_to_cat"],
            stats["cat_dataset_counts"],
        )

    with open(paths["id_to_id"], "w", encoding="utf-8") as f:
        _write_directional_percentages(
            f,
            "TASK ID -> TASK ID:",
            stats["id_to_id"],
            stats["id_dataset_counts"],
            stats["id_to_id"],
            stats["id_dataset_counts"],
        )

    return paths


def _write_mapping_section(f, title, values, lookup):
    found, not_in_hierarchy, not_reaching_top, not_found = _build_mapping_groups(values, lookup)
    f.write(f"{title}\n")
    f.write("SUMMARY:\n")
    f.write(f"FOUND: {len(found)}\n")
    f.write(f"NOT_IN_HIERARCHY: {len(not_in_hierarchy)}\n")
    f.write(f"IN_HIERARCHY_NOT_REACHING_TOPCONCEPT: {len(not_reaching_top)}\n")
    f.write(f"NOT_FOUND: {len(not_found)}\n\n")

    sections = [
        ("FOUND", found),
        ("NOT_IN_HIERARCHY", not_in_hierarchy),
        ("IN_HIERARCHY_NOT_REACHING_TOPCONCEPT", not_reaching_top),
        ("NOT_FOUND", not_found),
    ]
    for index, (header, lines) in enumerate(sections):
        f.write(f"{header}:\n")
        for line in lines:
            f.write(f"{line}\n")
        if index < len(sections) - 1:
            f.write("\n")


def write_counts_to_txt(records, output_path, lookup):
    stats = _compute_relation_stats(records)

    with open(output_path, 'w', encoding='utf-8') as f:
        _write_mapping_section(f, "TASK CATEGORIES -> MLUO THESAURUS:", stats["categories"], lookup)
        f.write("\n---\n\n")
        _write_mapping_section(f, "TASK IDS -> MLUO THESAURUS:", stats["ids"], lookup)

    return write_directional_files(stats, output_path)

if __name__ == "__main__":
    task_lookup = load_mluo_task_lookup(THESAURUS_PATH)
    for json_path, output_path in JSON_FILES:
        records = extract_task_records(json_path)
        if records:
            directional_paths = write_counts_to_txt(records, output_path, task_lookup)
            print(f"Résultat écrit dans {output_path}")
            for key in ["cat_to_id", "id_to_cat", "cat_to_cat", "id_to_id"]:
                print(f"Résultat écrit dans {directional_paths[key]}")
        else:
            print(f"Aucune donnée extraite pour {json_path}")
