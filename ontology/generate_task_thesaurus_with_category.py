import json
from pathlib import Path


TASK_SCHEME_MARKER = "## Task Scheme"
TASKS_JSON = Path.home() / "Downloads" / "tasks.json"
MLUO_TTL = Path(__file__).with_name("mluo.ttl")
TASK_CATEGORY_SOURCE = "<https://www.ibm.com/think/topics/machine-learning>"
TASK_SOURCE = "<https://www.huggingface.co/api/tasks>"


TASK_CATEGORY_CONCEPTS = [
    {
        "id": "supervised-tasks",
        "label": "Supervised Learning",
        "definition": "Supervised learning is a machine learning technique that uses labeled "
        "data sets to train artificial intelligence (AI) models to identify the underlying "
        "patterns and relationships. The goal of the learning process is to create a model "
        "that can predict correct outputs on new real-world data.",
    },
    {
        "id": "classification-tasks",
        "label": "Classification",
        "definition": "Classification in machine learning is a predictive modeling process "
        "by which machine learning models use classification algorithms to predict the "
        "correct label for input data.",
        "broader": "supervised-tasks",
    },
    {
        "id": "computer-vision-tasks",
        "label": "Computer Vision",
        "definition": "Computer vision is a subfield of artificial intelligence (AI) that "
        "equips machines with the ability to process, analyze and interpret visual inputs "
        "such as images and videos. It uses machine learning to help computers and other "
        "systems derive meaningful information from visual data.",
    },
    {
        "id": "feature-engineering-tasks",
        "label": "Feature Engineering",
        "definition": "Feature engineering preprocesses raw data into a machine-readable "
        "format. It optimizes ML model performance by transforming and selecting relevant "
        "features.",
    },
    {
        "id": "generative-ia-tasks",
        "label": "Generative AI",
        "definition": "Generative AI, sometimes called gen AI, is artificial intelligence "
        "(AI) that can create original content such as text, images, video, audio or "
        "software code in response to a user’s prompt or request.",
    },
    {
        "id": "multimodal-tasks",
        "label": "Multimodal AI",
        "definition": "Multimodal AI refers to machine learning models capable of processing "
        "and integrating information from multiple modalities or types of data. These "
        "modalities can include text, images, audio, video and other forms of sensory input.",
        "broader": "generative-ia-tasks",
    },
    {
        "id": "nlp-tasks",
        "label": "Natural Language Processing",
        "definition": "Natural language processing (NLP) is a subfield of computer science "
        "and artificial intelligence (AI) that uses machine learning to enable computers "
        "to understand and communicate with human language.",
    },
    {
        "id": "conversational-tasks",
        "label": "Conversational AI",
        "definition": "Conversational artificial intelligence (AI) refers to technologies, "
        "such as chatbots or virtual agents, that users can talk to. They use large volumes "
        "of data, machine learning and natural language processing to help imitate human "
        "interactions, recognizing speech and text inputs and translating their meanings "
        "across various languages.",
        "broader": "nlp-tasks",
    },
    {
        "id": "reinforcement-tasks",
        "label": "Reinforcement Learning",
        "definition": "Reinforcement learning (RL) is a type of machine learning process in "
        "which autonomous agents learn to make decisions by interacting with their environment.",
    },
]


def esc(text):
    return str(text or "").replace("\\", "\\\\").replace('"', '\\"').strip()


def first_text(value):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                if item.get("description"):
                    return str(item["description"]).strip()
                if item.get("id"):
                    return str(item["id"]).strip()
    return None


def first_str(value):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def task_broader(task_id):
    if "classification" in task_id:
        return "classification-tasks"
    if "regression" in task_id:
        return "supervised-tasks"
    if "question-answering" in task_id:
        return "conversational-tasks"
    if "feature-extraction" in task_id:
        return "feature-engineering-tasks"
    if "detection" in task_id or "segmentation" in task_id or "estimation" in task_id:
        return "computer-vision-tasks"
    if "reinforcement" in task_id:
        return "reinforcement-tasks"
    if task_id in {"automatic-speech-recognition", "translation", "summarization", 
                   "sentence-similarity", "text-ranking"}:
        return "nlp-tasks"
    if "generation" in task_id or task_id == "fill-mask":
        return "generative-ia-tasks"
    if "-to-" in task_id or task_id == "visual-document-retrieval":
        return "multimodal-tasks"
    return None


def print_task_assignments(tasks):
    grouped = {concept["id"]: [] for concept in TASK_CATEGORY_CONCEPTS}

    for task_id, task in tasks.items():
        category_id = task_broader(task_id)
        label = task.get("label", task_id)
        grouped.setdefault(category_id, []).append((task_id, label))

    print("\nTask categories and assigned tasks:")
    for concept in TASK_CATEGORY_CONCEPTS:
        category_id = concept["id"]
        category_label = concept["label"]
        entries = sorted(grouped.get(category_id, []), key=lambda item: item[0])

        print(f"\n=== {category_label} ({category_id}) ===")
        if not entries:
            print("- (no tasks)")
            continue

        for task_id, label in entries:
            print(f"- {task_id} | {label}")


def main():
    tasks = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    top_concept_ids = [concept["id"] for concept in TASK_CATEGORY_CONCEPTS if concept.get("broader") is None]

    lines = [
        TASK_SCHEME_MARKER,
        "mluo_th:TaskScheme a skos:ConceptScheme ;",
        '    skos:prefLabel "Machine Learning Task Scheme"@en ;',
        '    skos:definition "A controlled vocabulary for describing machine learning tasks."@en ;',
        "    skos:hasTopConcept ",
    ]

    for i, top_concept_id in enumerate(top_concept_ids):
        lines.append(
            f"        mluo_th:{top_concept_id}{',' if i < len(top_concept_ids)-1 else ' .'}"
        )
    lines.append("")

    for concept in TASK_CATEGORY_CONCEPTS:
        lines.extend(
            [
                f"mluo_th:{concept['id']} a skos:Concept, mluo:TaskCategory ;",
                f'    skos:prefLabel "{esc(concept["label"])}"@en ;',
                f'    skos:definition "{esc(concept["definition"])}"@en ;',
                f'    dcterms:source "{esc(TASK_CATEGORY_SOURCE)}"@en ;',
                "    skos:inScheme mluo_th:TaskScheme ;",
                "    skos:topConceptOf mluo_th:TaskScheme ." if concept.get("broader") is None else f"    skos:broader mluo_th:{concept['broader']} .",
                "",
            ]
        )

    for task_id, task in tasks.items():
        label = task.get("label", task_id)
        summary = task.get("summary", f"Task: {task_id}.")
        broader = task_broader(task_id)

        lines.extend(
            [
                f"mluo_th:{task_id} a skos:Concept, mluo:Task ;",
                f'    skos:prefLabel "{esc(label)}"@en ;',
                f'    skos:definition "{esc(summary)}"@en ;',
                f'    dcterms:source "{esc(TASK_SOURCE)}"@en ;',
            ]
        )

        examples = []
        if first_text(task.get("datasets")):
            examples.append(f"Dataset example: {first_text(task.get('datasets'))}")
        if first_text(task.get("models")):
            examples.append(f"Model example: {first_text(task.get('models'))}")
        if first_text(task.get("spaces")):
            examples.append(f"Demo example: {first_text(task.get('spaces'))}")
        if first_str(task.get("libraries")):
            examples.append(f"Library example: {first_str(task.get('libraries'))}.")
        if not examples:
            examples.append(f"Typical use case: {label}.")

        for ex in examples[:4]:
            lines.append(f'    skos:example "{esc(ex)}"@en ;')

        lines.append("    skos:inScheme mluo_th:TaskScheme ;")
        lines.append(f"    skos:broader mluo_th:{broader} ." if broader else "")
        lines.append("")

    # block = "\n".join(lines).rstrip() + "\n"
    # content = MLUO_TTL.read_text(encoding="utf-8")
    # if TASK_SCHEME_MARKER in content:
    #     content = content[: content.find(TASK_SCHEME_MARKER)].rstrip() + "\n\n" + block
    # else:
    #     content = content.rstrip() + "\n\n" + block
    # MLUO_TTL.write_text(content, encoding="utf-8")

    print(f"Updated {MLUO_TTL}")
    print_task_assignments(tasks)


if __name__ == "__main__":
    main()