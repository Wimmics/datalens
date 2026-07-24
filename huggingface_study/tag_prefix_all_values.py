from pathlib import Path
from collections import Counter
import json


def top_prefix_values_to_txt(
    input_dir: str | Path,
    output_file: str | Path,
    prefixes: list[str],
):
    """
    Recherche les valeurs les plus fréquentes après certains préfixes
    dans les tags des modèles Hugging Face et écrit les résultats
    dans un fichier texte.
    """

    input_dir = Path(input_dir)
    output_file = Path(output_file)

    counters = {prefix: Counter() for prefix in prefixes}

    for json_file in sorted(input_dir.glob("*.json")):
        print(f"Lecture : {json_file.name}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Impossible de lire {json_file}: {e}")
            continue

        if not isinstance(data, list):
            continue

        for obj in data:
            tags = obj.get("tags") or []

            for tag in tags:
                if not isinstance(tag, str):
                    continue

                for prefix in prefixes:
                    search = prefix + ":"

                    if tag.startswith(search):
                        value = tag[len(search):]
                        if value:
                            counters[prefix][value] += 1

    with open(output_file, "w", encoding="utf-8") as f:
        for prefix in prefixes:
            f.write(f"{prefix}\n")
            f.write("=" * len(prefix) + "\n")

            most_common = counters[prefix].most_common()

            if not most_common:
                f.write("Aucune occurrence\n\n")
                continue

            for value, count in most_common:
                f.write(f"{value} : {count}\n")

            f.write("\n")

    print(f"Résultats écrits dans : {output_file}")

prefixes = [
    "multilinguality",
    "diffusers",
    "loss",
]

top_prefix_values_to_txt(
    input_dir="_other\input\old\models_batches",
    output_file="top_prefix_values_models.txt",
    prefixes=prefixes,
)