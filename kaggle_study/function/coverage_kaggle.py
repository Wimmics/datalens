from collections import Counter

def analyse_tags_vers_txt(data, fichier="kaggle_study/stat/model_stats_tags.txt"):
    """
    Calcule occurrence et couverture des tags puis écrit le résultat dans un fichier txt.
    """

    total_documents = len(data)
    compteur_tags = Counter()

    for item in data:
        tags = item.get("Tags")

        if not tags:
            continue

        liste_tags = [
            tag.strip().lower()
            for tag in tags.split(",")
            if tag.strip()
        ]

        compteur_tags.update(set(liste_tags))

    resultats = []

    for tag, occurrence in compteur_tags.items():
        couverture = occurrence / total_documents if total_documents else 0

        resultats.append({
            "tag": tag,
            "occurrence": occurrence,
            "couverture": couverture
        })

    # Tri par occurrence décroissante
    resultats.sort(key=lambda x: x["occurrence"], reverse=True)

    # Écriture dans le fichier texte
    with open(fichier, "w", encoding="utf-8") as f:
        f.write(f"Nombre total de datasets : {total_documents}\n")
        f.write("=" * 60 + "\n\n")

        for r in resultats:
            f.write(
                f"Tag : {r['tag']}\n"
                f"Occurrence : {r['occurrence']}\n"
                f"Couverture : {r['couverture']:.2%}\n"
                f"{'-' * 60}\n"
            )

    return fichier

import json

with open("kaggle_study/raw_data/all_models.json", "r", encoding="utf-8") as f:
    datasets = json.load(f)

fichier_cree = analyse_tags_vers_txt(datasets)

print(f"Résultats enregistrés dans : {fichier_cree}")