import json
from pathlib import Path


TASK_SCHEME_MARKER = "## Task Scheme"
TASKS_JSON = Path.home() / "Downloads" / "tasks.json"
MLUO_TTL = Path(__file__).with_name("mluo.ttl")
TASK_SOURCE = "<https://www.huggingface.co/api/tasks>"


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


def main():
    tasks = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    task_ids = list(tasks.keys())

    lines = [
        TASK_SCHEME_MARKER,
        "mluo_th:TaskScheme a skos:ConceptScheme ;",
        '    skos:prefLabel "Machine Learning Task Scheme"@en ;',
        '    skos:definition "A controlled vocabulary for describing machine learning tasks."@en ;',
        "    skos:hasTopConcept ",
    ]

    for i, task_id in enumerate(task_ids):
        lines.append(f"        mluo_th:{task_id}{',' if i < len(task_ids)-1 else ' .'}")
    lines.append("")

    for task_id, task in tasks.items():
        label = task.get("label", task_id)
        summary = task.get("summary", f"Task: {task_id}.")

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
        lines.append("")

    block = "\n".join(lines).rstrip() + "\n"
    content = MLUO_TTL.read_text(encoding="utf-8")
    if TASK_SCHEME_MARKER in content:
        content = content[: content.find(TASK_SCHEME_MARKER)].rstrip() + "\n\n" + block
    else:
        content = content.rstrip() + "\n\n" + block
    MLUO_TTL.write_text(content, encoding="utf-8")

    print(f"Updated {MLUO_TTL}")


if __name__ == "__main__":
    main()
