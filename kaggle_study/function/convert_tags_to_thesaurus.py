import json
import re
from datetime import date

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, SKOS, DCTERMS, XSD


DLT = Namespace("http://ns.inria.fr/datalens/thesaurus/")
DLO = Namespace("http://ns.inria.fr/datalens/ontology/")
used_names = set()

CATEGORY_MAPPING = {
    "subject": {
        "scheme": "SubjectScheme",
        "class": "Subject",
    },
    "health and fitness": {
        "scheme": "HealthAndFitnessScheme",
        "class": "HealthAndFitness",
    },
    "geography and places": {
        "scheme": "GeographyAndPlacesScheme",
        "class": "GeographyAndPlaces",
    },
    "technique": {
        "scheme": "TechniqueScheme",
        "class": "Technique",
    },
    "data type": {
        "scheme": "DataTypeScheme",
        "class": "DataType",
    },
    "audience": {
        "scheme": "AudienceScheme",
        "class": "Audience",
    },
    "analysis": {
        "scheme": "AnalysisScheme",
        "class": "Analysis",
    },
    "task": {
        "scheme": "TaskScheme",
        "class": "Task",
    },
    "packages": {
        "scheme": "PackageScheme",
        "class": "Package",
    },
    "algorithms": {
        "scheme": "AlgorithmScheme",
        "class": "Algorithm",
    },
    "admin": {
        "scheme": "AdminScheme",
        "class": "Admin",
    },
    "language": {
        "scheme": "LanguageScheme",
        "class": "Language",
    },
    "architecture": {
        "scheme": "ArchitectureScheme",
        "class": "Architecture",
    },
}

def pascal_case(value: str) -> str:
    """Generate PascalCase Turtle local names."""

    value = value.replace("_", " ").replace("-", " ")

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", value)
    value = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", value)

    words = re.findall(r"[A-Za-z0-9]+", value)

    if not words:
        return "Item"

    return "".join(word[:1].upper() + word[1:] for word in words)


def uri_name(raw_value: str, used_names: set[str]) -> str:
    base_name = pascal_case(raw_value)

    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        suffix += 1

def class_name(category: str) -> str:
    return CATEGORY_MAPPING.get(category, {}).get("class", "")

def scheme_name(category: str) -> str:
    return CATEGORY_MAPPING.get(category, {}).get("scheme", "")

def json_to_skos(tags_json: str, output_ttl: str):

    with open(tags_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    g = Graph()

    g.bind("dcterms", DCTERMS)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)
    g.bind("dlo", DLO)
    g.bind("dlt", DLT)

    def add_node(label, info, scheme, parent=None):

        concept = DLT[uri_name(label, used_names)]

        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept, SKOS.inScheme, scheme))

        definition = info.get("description")
        if definition:
            g.add((concept, SKOS.definition,
                   Literal(definition, lang="en")))

        if parent is not None:
            g.add((concept, SKOS.broader, parent))
            g.add((parent, SKOS.narrower, concept))

        for child_label, child_info in info.get("children", {}).items():
            add_node(child_label, child_info, scheme, concept)

    for category, category_info in data.items():

        if category not in CATEGORY_MAPPING:
            raise ValueError(f"Catégorie inconnue : {category}")

        mapping = CATEGORY_MAPPING[category]

        scheme = DLT[mapping["scheme"]]
        scheme_class = DLO[mapping["class"]]

        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, RDF.type, scheme_class))
        g.add((scheme, SKOS.prefLabel, Literal(category, lang="en")))

        for label, info in category_info.get("children", {}).items():
            add_node(label, info, scheme)

    g.serialize(output_ttl, format="turtle")

json_to_skos(
    tags_json="huggingface_study/tags.json",
    output_ttl="ontology/kaggle_tags.ttl",
)