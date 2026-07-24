import re

from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
import unicodedata
from typing import Dict, List, Any
import json

STOPWORDS = {
    "and",
    "the",
    "for",
    "of",
    "to",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()

    words = re.findall(r"[a-z0-9]+", text)
    words = [w for w in words if w not in STOPWORDS]

    return "".join(words)

def extract_tags_by_category(tags_json: str) -> Dict[str, List[str]]:
    """
    Extrait tous les noms de tags de chaque catégorie du fichier tags.json.

    Parameters
    ----------
    tags_json : str
        Chemin vers le fichier tags.json.

    Returns
    -------
    dict
        {
            "subject": [...],
            "task": [...],
            "techniques": [...],
            ...
        }
    """

    with open(tags_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}

    def traverse(node: Dict[str, Any], tags: List[str]):
        for name, info in node.items():
            tags.append(name)

            children = info.get("children", {})
            if children:
                traverse(children, tags)

    for category, category_data in data.items():

        tags = []

        traverse(category_data.get("children", {}), tags)

        result[category] = sorted(set(tags))

    return result


def compare_tags_to_scheme(
    graph: Graph,
    tags: dict,
    category: str,
    scheme_uri: str,
):
    """
    Compare les tags d'une catégorie avec les concepts d'un ConceptScheme.

    Parameters
    ----------
    graph : rdflib.Graph
        Graphe contenant le thesaurus.

    tags : dict
        Dictionnaire des tags.

    category : str
        Exemple : 'task', 'subject', 'techniques'.

    scheme_uri : str
        URI du ConceptScheme.

    Returns
    -------
    dict
    """

    scheme = URIRef(scheme_uri)

    # ----------------------------
    # Construction de l'index du thesaurus
    # ----------------------------

    concept_index = {}

    for concept in graph.subjects(SKOS.inScheme, scheme):

        labels = set()

        for lbl in graph.objects(concept, SKOS.prefLabel):
            labels.add(str(lbl))

        for lbl in graph.objects(concept, SKOS.altLabel):
            labels.add(str(lbl))

        for label in labels:
            concept_index[normalize(label)] = {
                "uri": str(concept),
                "label": label,
            }

    # ----------------------------
    # Comparaison
    # ----------------------------

    matches = []
    missing_tags = []
    matched_concepts = set()

    for tag in tags.get(category, []):

        key = normalize(tag)

        if key in concept_index:

            concept = concept_index[key]

            matches.append(
                {
                    "tag": tag,
                    "concept_label": concept["label"],
                    "concept_uri": concept["uri"],
                }
            )

            matched_concepts.add(concept["uri"])

        else:

            missing_tags.append(tag)

    # ----------------------------
    # Concepts non utilisés
    # ----------------------------

    unused_concepts = []

    for concept in graph.subjects(SKOS.inScheme, scheme):

        if str(concept) not in matched_concepts:

            label = next(graph.objects(concept, SKOS.prefLabel), None)

            unused_concepts.append(
                {
                    "label": str(label),
                    "uri": str(concept),
                }
            )

    # ----------------------------
    # Statistiques
    # ----------------------------

    nb_tags = len(tags.get(category, []))
    nb_concepts = len(
        list(graph.subjects(SKOS.inScheme, scheme))
    )

    nb_matches = len(matches)

    tag_coverage = (
        100 * nb_matches / nb_tags
        if nb_tags
        else 0
    )

    concept_coverage = (
        100 * len(matched_concepts) / nb_concepts
        if nb_concepts
        else 0
    )

    return {

        "statistics": {

            "category": category,

            "scheme": scheme_uri,

            "nb_tags": nb_tags,

            "nb_concepts": nb_concepts,

            "matched_tags": nb_matches,

            "missing_tags": len(missing_tags),

            "unused_concepts": len(unused_concepts),

            "tag_coverage_percent": round(tag_coverage, 2),

            "concept_coverage_percent": round(concept_coverage, 2),
        },

        "matches": sorted(matches, key=lambda x: x["tag"]),

        "missing_tags": sorted(missing_tags),

        "unused_concepts": sorted(
            unused_concepts,
            key=lambda x: x["label"],
        ),
    }

from rdflib import Graph

g = Graph()
g.parse("ontology/model_config_thesaurus_v0.ttl", format="turtle")

tags = extract_tags_by_category("huggingface_study/tags.json")

# print(tags.keys())
# # dict_keys(['subject', 'task', 'techniques', ...])

# print(len(tags["subject"]))
# print(tags["subject"][:20])

# print(len(tags["task"]))
# print(tags["task"][:20])

result = compare_tags_to_scheme(
    graph=g,
    tags=tags,
    category="algorithms",
    scheme_uri="http://ns.inria.fr/datalens/thesaurus/TaskScheme",
)



with open(f"kaggle_study/tag_comparison/{result['statistics']['category']}_comparison_{result['statistics']['scheme'].split('/')[-1]}.txt", "w", encoding="utf-8") as f:
    write = f.write
    write(f"Comparaison des tags de la catégorie {result['statistics']['category']} avec {result['statistics']['scheme'].split('/')[-1]}\n")
    write(f"Nombre de tags : {result['statistics']['nb_tags']}\n")
    write(f"Nombre de concepts : {result['statistics']['nb_concepts']}\n")
    write(f"Nombre de tags correspondants : {result['statistics']['matched_tags']}\n")
    write(f"Couverture des tags : {result['statistics']['tag_coverage_percent']}%\n")
    write("Correspondances\n")
    for m in result["matches"]:
        write(f"{m['tag']} -> {m['concept_label']}\n")
    write("\nTags absents\n")
    for t in result["missing_tags"]:
        write(f"{t}\n")