import json


# Paramètres à modifier directement ici
INPUT_FILE = "case-study\data\input\datasets_new.json"
OUTPUT_FILE = "case-study\data\input\dataset_new_extract.json"
LIMIT = 10000


def extract_first_objects(input_file: str, output_file: str, limit: int = 10000) -> None:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Le JSON doit être une liste d'objets.")

    first_items = data[:limit]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(first_items, f, ensure_ascii=False, indent=2)

    print(f"{len(first_items)} objets écrits dans : {output_file}")


if __name__ == "__main__":
    extract_first_objects(INPUT_FILE, OUTPUT_FILE, LIMIT)
