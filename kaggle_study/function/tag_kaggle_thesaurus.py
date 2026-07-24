import csv
import json
import re
from collections import defaultdict

from rdflib import Graph
from rdflib.namespace import RDF, SKOS
from rapidfuzz import process, fuzz


# -----------------------------------------------------
# Normalisation
# -----------------------------------------------------

def normalize(text: str) -> str:
    text = text.lower()

    text = text.replace("&", " and ")

    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")

    text = re.sub(r"[^\w\s]", "", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# -----------------------------------------------------
# Chargement des tags Kaggle
# -----------------------------------------------------

def load_tags(csv_file):

    tags = []
    exact = {}

    with open(csv_file, encoding="utf-8", newline="") as f:

        reader = csv.DictReader(f)

        for row in reader:

            tag = {
                "id": int(row["Id"]),
                "parent_id": int(row["ParentTagId"]) if row["ParentTagId"] else None,
                "name": row["Name"],
                "slug": row["Slug"],
                "full_path": row["FullPath"],
                "description": row["Description"],
                "dataset_count": int(row["DatasetCount"]),
                "competition_count": int(row["CompetitionCount"]),
                "kernel_count": int(row["KernelCount"]),
            }

            tags.append(tag)

            exact[row["Name"].lower()] = tag
            exact[row["Slug"].lower()] = tag
            exact[normalize(row["Name"])] = tag
            exact[normalize(row["Slug"])] = tag

    return tags, exact


# -----------------------------------------------------
# Recherche
# -----------------------------------------------------

def find_best_match(label, tags, exact):

    key = label.lower()

    if key in exact:
        return exact[key], 100, "exact"

    key = normalize(label)

    if key in exact:
        return exact[key], 99, "normalized"

    candidates = [
        normalize(t["name"])
        for t in tags
    ]

    best, score, idx = process.extractOne(
        key,
        candidates,
        scorer=fuzz.WRatio
    )

    if score >= 92:
        return tags[idx], score, "fuzzy"

    return None, score, None


# -----------------------------------------------------
# Comparaison
# -----------------------------------------------------

def compare(csv_file, ttl_file, output):

    tags, exact = load_tags(csv_file)

    graph = Graph()
    graph.parse(ttl_file, format="turtle")

    results = defaultdict(list)

    for scheme in graph.subjects(RDF.type, SKOS.ConceptScheme):

        scheme_name = str(graph.value(scheme, SKOS.prefLabel))

        for concept in graph.subjects(SKOS.inScheme, scheme):

            labels = []

            labels.extend(
                str(x)
                for x in graph.objects(concept, SKOS.prefLabel)
            )

            labels.extend(
                str(x)
                for x in graph.objects(concept, SKOS.altLabel)
            )

            matched = False

            for label in labels:

                tag, score, method = find_best_match(
                    label,
                    tags,
                    exact
                )

                if tag is None:
                    continue

                results[scheme_name].append({

                    "match_score": score,
                    "match_method": method,

                    "concept": {
                        "uri": str(concept),
                        "prefLabel": str(
                            graph.value(
                                concept,
                                SKOS.prefLabel
                            )
                        ),
                        "definition": (
                            None
                            if graph.value(concept, SKOS.definition) is None
                            else str(
                                graph.value(
                                    concept,
                                    SKOS.definition
                                )
                            )
                        ),
                        "altLabels": [
                            str(x)
                            for x in graph.objects(
                                concept,
                                SKOS.altLabel
                            )
                        ]
                    },

                    "kaggle_tag": tag

                })

                matched = True
                break

            if not matched:

                results[scheme_name].append({

                    "match_score": 0,
                    "match_method": None,

                    "concept": {
                        "uri": str(concept),
                        "prefLabel": str(
                            graph.value(
                                concept,
                                SKOS.prefLabel
                            )
                        ),
                        "definition": (
                            None
                            if graph.value(concept, SKOS.definition) is None
                            else str(
                                graph.value(
                                    concept,
                                    SKOS.definition
                                )
                            )
                        )
                    },

                    "kaggle_tag": None

                })

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("Terminé.")


if __name__ == "__main__":

    compare(
        csv_file="meta_kaggle_raw/Tags.csv",
        ttl_file="ontology/datalens_th.ttl",
        output="kaggle_study/matches.json"
    )