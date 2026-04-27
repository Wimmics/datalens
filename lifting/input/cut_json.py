import json
from pathlib import Path


# Paramètres à modifier directement ici
INPUT_FILE = "c:/Users/sunburst-user/Documents/datalens/lifting/input/models.json"
OUTPUT_FILE = "c:/Users/sunburst-user/Documents/datalens/lifting/input/models_extract.json"
LIMIT = 10000

def extract_first_objects(input_file: str, output_file: str, limit: int = 10000) -> None:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable: {input_path}. Verifie le nom (ex: datasets.json) et le chemin."
        )

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Le JSON doit être une liste d'objets.")

    first_items = data[:limit]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(first_items, f, ensure_ascii=False, indent=2)

    print(f"{len(first_items)} objets écrits dans : {output_path}")


if __name__ == "__main__":
    extract_first_objects(INPUT_FILE, OUTPUT_FILE, LIMIT)
