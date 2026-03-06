import argparse
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IDS_TO_CATEGORY_REPORT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "datasets_new_ids_to_category.txt")
)
DEFAULT_IDS_TO_IDS_REPORT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "datasets_new_ids_to_ids.txt")
)
DEFAULT_MISSING_TASKS_REPORT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "case-study", "thesaurus_stats", "datasets_new_0.txt")
)
DEFAULT_THESAURUS_PATH = os.path.join(SCRIPT_DIR, "mluo_thesaurus.ttl")


def normalize_task(value):
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return normalized.strip("-")


def task_id_to_label(task_id):
    words = task_id.replace("-", " ").split()
    return " ".join(word.capitalize() for word in words)


def load_mluo_task_lookup(ttl_path):
    with open(ttl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    lookup = {}
    existing_concepts = set()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:(Task|TaskCategory) ;$", line)
        if not match:
            i += 1
            continue

        local_name = match.group(1)
        kind = match.group(2)
        existing_concepts.add(local_name)

        pref_label = None
        block_lines = []
        j = i + 1
        while j < len(lines):
            block_line = lines[j].strip()
            block_lines.append(block_line)
            label_match = re.match(r'^skos:prefLabel "([^"]+)"@en ;$', block_line)
            if label_match:
                pref_label = label_match.group(1)
            if block_line.endswith("."):
                break
            j += 1

        concept_uri = f"mluo_th:{local_name}"
        for candidate in [local_name, pref_label]:
            if candidate:
                key = normalize_task(candidate)
                lookup[key] = {
                    "uri": concept_uri,
                    "kind": kind,
                }

        i = j + 1

    return lookup, existing_concepts


def parse_ids_to_category_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    sections = []
    current = None

    for line in lines:
        if not line.strip() or line.startswith("TASK ID -> TASK CATEGORY:"):
            continue

        header_match = re.match(r"^(.+?) \((\d+) datasets\):$", line)
        if header_match:
            if current:
                sections.append(current)
            current = {
                "task_id": header_match.group(1).strip(),
                "dataset_count": int(header_match.group(2)),
                "relations": [],
            }
            continue

        relation_match = re.match(
            r"^\s{2}(.+?):\s+(\d+)\s+\(([0-9]+(?:\.[0-9]+)?)%\)\s+\|\s+reverse:\s+([0-9]+(?:\.[0-9]+)?)%$",
            line,
        )
        if relation_match and current:
            current["relations"].append(
                {
                    "task_category": relation_match.group(1).strip(),
                    "count": int(relation_match.group(2)),
                    "forward_pct": float(relation_match.group(3)),
                    "reverse_pct": float(relation_match.group(4)),
                }
            )

    if current:
        sections.append(current)

    return sections


def parse_ids_to_ids_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    sections = []
    current = None

    for line in lines:
        if not line.strip() or line.startswith("TASK ID -> TASK ID:"):
            continue

        header_match = re.match(r"^(.+?) \((\d+) datasets\):$", line)
        if header_match:
            if current:
                sections.append(current)
            current = {
                "task_id": header_match.group(1).strip(),
                "dataset_count": int(header_match.group(2)),
                "relations": [],
            }
            continue

        relation_match = re.match(
            r"^\s{2}(.+?):\s+(\d+)\s+\(([0-9]+(?:\.[0-9]+)?)%\)\s+\|\s+reverse:\s+([0-9]+(?:\.[0-9]+)?)%$",
            line,
        )
        if relation_match and current:
            current["relations"].append(
                {
                    "task_id": relation_match.group(1).strip(),
                    "count": int(relation_match.group(2)),
                    "forward_pct": float(relation_match.group(3)),
                    "reverse_pct": float(relation_match.group(4)),
                }
            )

    if current:
        sections.append(current)

    return sections


def parse_missing_task_ids_from_zero_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    in_supported_section = False
    in_not_found_section = False
    missing_task_ids = []
    seen_local_names = set()

    for line in lines:
        stripped = line.strip()

        if stripped in {"TASK CATEGORIES -> MLUO THESAURUS:", "TASK IDS -> MLUO THESAURUS:"}:
            in_supported_section = True
            in_not_found_section = False
            continue

        if not in_supported_section:
            continue

        if stripped == "NOT_FOUND:":
            in_not_found_section = True
            continue

        if stripped == "FOUND:":
            in_not_found_section = False
            continue

        if stripped == "---":
            in_supported_section = False
            in_not_found_section = False
            continue

        if not in_not_found_section or not stripped:
            continue

        match = re.match(r"^([^:]+):\s+\d+$", stripped)
        if match:
            task_id = match.group(1).strip()
            local_name = normalize_task(task_id)
            if local_name and local_name not in seen_local_names:
                missing_task_ids.append(task_id)
                seen_local_names.add(local_name)

    return missing_task_ids


def build_new_task_blocks(
    report_sections,
    lookup,
    existing_concepts,
    min_datasets,
    min_forward,
    fallback_min_forward,
    max_reverse,
):
    blocks = []
    skipped_existing = []
    skipped_no_broader = []

    for section in report_sections:
        task_id = section["task_id"]
        dataset_count = section["dataset_count"]
        local_name = normalize_task(task_id)

        if dataset_count <= min_datasets:
            continue
        if local_name in existing_concepts:
            skipped_existing.append(task_id)
            continue

        broader_uris = []
        for relation in section["relations"]:
            if relation["forward_pct"] <= min_forward:
                continue
            if relation["reverse_pct"] >= max_reverse:
                continue

            key = normalize_task(relation["task_category"])
            mapped = lookup.get(key)
            if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                broader_uris.append(mapped["uri"])

        broader_uris = sorted(set(broader_uris))

        if len(broader_uris) == 1 and fallback_min_forward < min_forward:
            relaxed_broader_uris = []
            for relation in section["relations"]:
                if relation["forward_pct"] <= fallback_min_forward:
                    continue
                if relation["reverse_pct"] >= max_reverse:
                    continue

                key = normalize_task(relation["task_category"])
                mapped = lookup.get(key)
                if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                    relaxed_broader_uris.append(mapped["uri"])

            broader_uris = sorted(set(relaxed_broader_uris))

        if not broader_uris:
            skipped_no_broader.append(task_id)
            continue

        label = task_id_to_label(task_id).replace('"', '\\"')
        broader_tail = ",\n        ".join(broader_uris)
        block = (
            f"mluo_th:{local_name} a skos:Concept, mluo:Task ;\n"
            f"    skos:prefLabel \"{label}\"@en ;\n"
            f"    skos:inScheme mluo_th:TaskScheme ;\n"
            f"    skos:broader {broader_tail} .\n"
        )
        blocks.append(block)

    return blocks, skipped_existing, skipped_no_broader


def add_blocks_to_lookup(lookup, blocks):
    for block in blocks:
        header_match = re.search(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:Task ;", block, re.MULTILINE)
        if not header_match:
            continue

        local_name = header_match.group(1)
        label_match = re.search(r'^\s*skos:prefLabel "([^"]+)"@en ;$', block, re.MULTILINE)
        concept_uri = f"mluo_th:{local_name}"

        lookup[normalize_task(local_name)] = {
            "uri": concept_uri,
            "kind": "Task",
        }
        if label_match:
            lookup[normalize_task(label_match.group(1))] = {
                "uri": concept_uri,
                "kind": "Task",
            }


def build_ids_to_ids_broader_map(
    report_sections,
    lookup,
    min_datasets,
    min_forward,
    fallback_min_forward,
    max_reverse,
):
    broader_by_local_name = {}

    for section in report_sections:
        task_id = section["task_id"]
        dataset_count = section["dataset_count"]
        task_local_name = normalize_task(task_id)

        if dataset_count <= min_datasets:
            continue

        broader_uris = []
        for relation in section["relations"]:
            if relation["forward_pct"] <= min_forward:
                continue
            if relation["reverse_pct"] >= max_reverse:
                continue

            key = normalize_task(relation["task_id"])
            mapped = lookup.get(key)
            if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                broader_uris.append(mapped["uri"])

        broader_uris = sorted(set(broader_uris))

        if len(broader_uris) == 1 and fallback_min_forward < min_forward:
            relaxed_broader_uris = []
            for relation in section["relations"]:
                if relation["forward_pct"] <= fallback_min_forward:
                    continue
                if relation["reverse_pct"] >= max_reverse:
                    continue

                key = normalize_task(relation["task_id"])
                mapped = lookup.get(key)
                if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                    relaxed_broader_uris.append(mapped["uri"])

            broader_uris = sorted(set(relaxed_broader_uris))

        if broader_uris:
            broader_by_local_name[task_local_name] = broader_uris

    return broader_by_local_name


def build_ids_to_category_broader_map(
    report_sections,
    lookup,
    min_datasets,
    min_forward,
    fallback_min_forward,
    max_reverse,
):
    broader_by_local_name = {}

    for section in report_sections:
        task_id = section["task_id"]
        dataset_count = section["dataset_count"]
        task_local_name = normalize_task(task_id)

        if dataset_count <= min_datasets:
            continue

        broader_uris = []
        for relation in section["relations"]:
            if relation["forward_pct"] <= min_forward:
                continue
            if relation["reverse_pct"] >= max_reverse:
                continue

            key = normalize_task(relation["task_category"])
            mapped = lookup.get(key)
            if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                broader_uris.append(mapped["uri"])

        broader_uris = sorted(set(broader_uris))

        if len(broader_uris) == 1 and fallback_min_forward < min_forward:
            relaxed_broader_uris = []
            for relation in section["relations"]:
                if relation["forward_pct"] <= fallback_min_forward:
                    continue
                if relation["reverse_pct"] >= max_reverse:
                    continue

                key = normalize_task(relation["task_category"])
                mapped = lookup.get(key)
                if mapped and mapped["kind"] in {"Task", "TaskCategory"}:
                    relaxed_broader_uris.append(mapped["uri"])

            broader_uris = sorted(set(relaxed_broader_uris))

        if broader_uris:
            broader_by_local_name[task_local_name] = broader_uris

    return broader_by_local_name


def merge_broader_maps(*maps):
    merged = {}
    for broader_map in maps:
        for local_name, uris in broader_map.items():
            merged[local_name] = sorted(set(merged.get(local_name, []) + uris))
    return merged


def enrich_blocks_with_broader_map(blocks, broader_by_local_name):
    updated_blocks = []
    updated_count = 0

    for block in blocks:
        header_match = re.search(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:Task ;", block, re.MULTILINE)
        if not header_match:
            updated_blocks.append(block)
            continue

        local_name = header_match.group(1)
        new_broader_uris = broader_by_local_name.get(local_name)
        if not new_broader_uris:
            updated_blocks.append(block)
            continue

        broader_match = re.search(r"^\s*skos:broader\s+(.+?)\s*\.$", block, re.MULTILINE | re.DOTALL)
        if broader_match:
            existing_broader_uris = re.findall(r"mluo_th:[A-Za-z0-9\-]+", broader_match.group(1))
            merged_broader_uris = sorted(set(existing_broader_uris + new_broader_uris))
            broader_tail = ",\n        ".join(merged_broader_uris)
            updated_block = re.sub(
                r"^\s*skos:broader\s+(.+?)\s*\.$",
                f"    skos:broader {broader_tail} .",
                block,
                count=1,
                flags=re.MULTILINE | re.DOTALL,
            )
        else:
            broader_tail = ",\n        ".join(new_broader_uris)
            updated_block = block.replace(
                "    skos:inScheme mluo_th:TaskScheme .",
                f"    skos:inScheme mluo_th:TaskScheme ;\n    skos:broader {broader_tail} .",
            )

        if updated_block != block:
            updated_count += 1
        updated_blocks.append(updated_block)

    return updated_blocks, updated_count


def build_missing_task_blocks_without_broader(task_ids, existing_concepts, selected_local_names):
    blocks = []
    skipped_existing_or_selected = []

    for task_id in task_ids:
        local_name = normalize_task(task_id)

        if local_name in existing_concepts or local_name in selected_local_names:
            skipped_existing_or_selected.append(task_id)
            continue

        label = task_id_to_label(task_id).replace('"', '\\"')
        block = (
            f"mluo_th:{local_name} a skos:Concept, mluo:Task ;\n"
            f"    skos:prefLabel \"{label}\"@en ;\n"
            f"    skos:inScheme mluo_th:TaskScheme .\n"
        )
        blocks.append(block)

    return blocks, skipped_existing_or_selected


def extract_selected_local_names(blocks):
    local_names = set()
    for block in blocks:
        match = re.match(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:Task ;", block)
        if match:
            local_names.add(match.group(1))
    return local_names


def append_blocks_to_thesaurus(ttl_path, blocks):
    with open(ttl_path, "a", encoding="utf-8") as f:
        f.write("\n\n## Tasks not in API\n")
        for block in blocks:
            f.write("\n")
            f.write(block)


def enrich_existing_task_blocks_in_thesaurus(ttl_path, broader_by_local_name, apply_changes):
    with open(ttl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_any = False
    updated_count = 0
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        start_match = re.match(r"^mluo_th:([A-Za-z0-9\-]+) a skos:Concept, mluo:Task ;$", line)
        if not start_match:
            i += 1
            continue

        j = i + 1
        while j < len(lines):
            if lines[j].strip().endswith("."):
                break
            j += 1
        if j >= len(lines):
            break

        block = "".join(lines[i : j + 1])
        updated_blocks, changed = enrich_blocks_with_broader_map([block], broader_by_local_name)
        if changed:
            replacement = updated_blocks[0]
            if not replacement.endswith("\n"):
                replacement += "\n"
            replacement_lines = replacement.splitlines(keepends=True)
            lines[i : j + 1] = replacement_lines
            updated_any = True
            updated_count += 1
            j = i + len(replacement_lines) - 1

        i = j + 1

    if apply_changes and updated_any:
        with open(ttl_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Add task IDs to mluo_thesaurus.ttl for IDs with more than N datasets, "
            "and task categories where forward percentage is above threshold and reverse percentage is below threshold."
        )
    )
    parser.add_argument("--report", default=DEFAULT_IDS_TO_CATEGORY_REPORT_PATH, help="Path to datasets_new_ids_to_category.txt")
    parser.add_argument(
        "--ids-to-ids-report",
        default=DEFAULT_IDS_TO_IDS_REPORT_PATH,
        help="Path to datasets_new_ids_to_ids.txt",
    )
    parser.add_argument(
        "--missing-tasks-report",
        default=DEFAULT_MISSING_TASKS_REPORT_PATH,
        help="Path to datasets_new_0.txt (TASK CATEGORIES/TASK IDS -> NOT_FOUND source)",
    )
    parser.add_argument("--thesaurus", default=DEFAULT_THESAURUS_PATH, help="Path to mluo_thesaurus.ttl")
    parser.add_argument("--min-datasets", type=int, default=0, help="Minimum dataset count (strictly greater)")
    parser.add_argument("--min-forward", type=float, default=90.0, help="Forward percentage threshold (strictly greater)")
    parser.add_argument(
        "--fallback-min-forward",
        type=float,
        default=80.0,
        help="Fallback forward threshold used only when exactly one broader is found at --min-forward",
    )
    parser.add_argument("--max-reverse", type=float, default=80.0, help="Reverse percentage threshold (strictly lower)")
    parser.add_argument("--skip-ids-categories", action="store_true", help="Skip IDs->Category concept block generation")
    parser.add_argument("--skip-ids-ids", action="store_true", help="Skip IDs->IDs broader enrichment")
    parser.add_argument("--apply", action="store_true", help="Apply changes to thesaurus (default is dry-run)")
    args = parser.parse_args()

    if not os.path.exists(args.report):
        raise FileNotFoundError(f"Report not found: {args.report}")
    if not os.path.exists(args.ids_to_ids_report):
        raise FileNotFoundError(f"IDs-to-IDs report not found: {args.ids_to_ids_report}")
    if not os.path.exists(args.missing_tasks_report):
        raise FileNotFoundError(f"Missing-tasks report not found: {args.missing_tasks_report}")
    if not os.path.exists(args.thesaurus):
        raise FileNotFoundError(f"Thesaurus not found: {args.thesaurus}")

    lookup, existing_concepts = load_mluo_task_lookup(args.thesaurus)

    blocks = []
    blocks_without_broader = []
    skipped_existing = []
    skipped_no_broader = []
    skipped_existing_or_selected_without_broader = []
    ids_to_ids_broader_applied = 0
    ids_to_ids_broader_applied_existing = 0
    ids_to_ids_broader_applied_missing = 0
    ids_to_ids_broader_applied_in_thesaurus = 0
    ids_to_category_broader_applied_in_thesaurus = 0
    sections = []
    if not args.skip_ids_categories:
        sections = parse_ids_to_category_report(args.report)
        blocks, skipped_existing, skipped_no_broader = build_new_task_blocks(
            sections,
            lookup,
            existing_concepts,
            args.min_datasets,
            args.min_forward,
            args.fallback_min_forward,
            args.max_reverse,
        )

        selected_local_names = extract_selected_local_names(blocks)
        missing_task_ids = parse_missing_task_ids_from_zero_report(args.missing_tasks_report)
        blocks_without_broader, skipped_existing_or_selected_without_broader = build_missing_task_blocks_without_broader(
            missing_task_ids,
            existing_concepts,
            selected_local_names,
        )

    combined_broader_by_local_name = {}
    if not args.skip_ids_categories:
        ids_to_category_broader_by_local_name = build_ids_to_category_broader_map(
            sections,
            lookup,
            args.min_datasets,
            args.min_forward,
            args.fallback_min_forward,
            args.max_reverse,
        )
        combined_broader_by_local_name = merge_broader_maps(combined_broader_by_local_name, ids_to_category_broader_by_local_name)

    if not args.skip_ids_ids:
        lookup_with_generated = dict(lookup)
        add_blocks_to_lookup(lookup_with_generated, blocks)
        add_blocks_to_lookup(lookup_with_generated, blocks_without_broader)

        ids_to_ids_sections = parse_ids_to_ids_report(args.ids_to_ids_report)
        broader_by_local_name = build_ids_to_ids_broader_map(
            ids_to_ids_sections,
            lookup_with_generated,
            args.min_datasets,
            args.min_forward,
            args.fallback_min_forward,
            args.max_reverse,
        )
        combined_broader_by_local_name = merge_broader_maps(combined_broader_by_local_name, broader_by_local_name)

    if combined_broader_by_local_name:
        blocks, ids_to_ids_broader_applied_existing = enrich_blocks_with_broader_map(
            blocks,
            combined_broader_by_local_name,
        )
        blocks_without_broader, ids_to_ids_broader_applied_missing = enrich_blocks_with_broader_map(
            blocks_without_broader,
            combined_broader_by_local_name,
        )
        ids_to_ids_broader_applied_in_thesaurus = enrich_existing_task_blocks_in_thesaurus(
            args.thesaurus,
            combined_broader_by_local_name,
            args.apply,
        )
        ids_to_category_broader_applied_in_thesaurus = ids_to_ids_broader_applied_in_thesaurus
        ids_to_ids_broader_applied = (
            ids_to_ids_broader_applied_existing
            + ids_to_ids_broader_applied_missing
            + ids_to_ids_broader_applied_in_thesaurus
        )

    all_blocks = blocks + blocks_without_broader

    print(f"Candidate task blocks: {len(blocks)}")
    print(f"Candidate missing task blocks without broader: {len(blocks_without_broader)}")
    print(f"Skipped task blocks (already exists in thesaurus): {len(skipped_existing)}")
    print(f"Skipped (no matching broader category after filters): {len(skipped_no_broader)}")
    print(
        "Skipped missing task blocks without broader (already exists/selected): "
        f"{len(skipped_existing_or_selected_without_broader)}"
    )
    print(f"Broader enrichments applied (generated blocks with broader): {ids_to_ids_broader_applied_existing}")
    print(f"Broader enrichments applied (generated blocks without broader): {ids_to_ids_broader_applied_missing}")
    print(f"Broader enrichments applied (existing thesaurus blocks): {ids_to_ids_broader_applied_in_thesaurus}")
    print(f"Broader enrichments applied (total): {ids_to_ids_broader_applied}")

    if not all_blocks:
        print("No additions to apply.")
        return

    if args.apply:
        append_blocks_to_thesaurus(args.thesaurus, all_blocks)
        print(f"Appended {len(all_blocks)} task blocks to: {args.thesaurus}")
    else:
        print("Dry-run mode. Use --apply to append to thesaurus.")
        if all_blocks:
            print("\nPreview first task block:\n")
            print(all_blocks[0])


if __name__ == "__main__":
    main()
