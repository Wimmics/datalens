import csv
import json


def csv_tags_to_json_tree(csv_file, json_file=None):
    tree = {}

    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            parts = [p.strip() for p in row["FullPath"].split(">")]

            current = tree

            for part in parts[:-1]:
                current = current.setdefault(part, {"children": {}})["children"]

            leaf = parts[-1]
            current.setdefault(leaf, {
                "id": int(row["Id"]),
                "parent_id": int(row["ParentTagId"]) if row["ParentTagId"] else None,
                "slug": row["Slug"],
                "description": row["Description"],
                "dataset_count": int(row["DatasetCount"]),
                "competition_count": int(row["CompetitionCount"]),
                "kernel_count": int(row["KernelCount"]),
                "children": {}
            })

    if json_file:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=4)

    return tree

if __name__ == "__main__":

    csv_tags_to_json_tree(r"meta_kaggle_raw\Tags.csv", r"kaggle_study\tags.json")