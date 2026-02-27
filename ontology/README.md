# MLUO Thesaurus

`mluo_thesaurus.ttl` is a SKOS thesaurus used to describe machine learning datasets and tasks with a controlled vocabulary.

## What the thesaurus contains

- An ontology header (`owl:Ontology`) with metadata (title, creators, version, dates, license).
- A **Modality Scheme** (`mluo_th:ModalityScheme`) with concepts of modalities such as `Text`, `Image`, `Audio`, etc.
- A **Task Scheme** (`mluo_th:TaskScheme`) with:
	- task categories (`mluo:TaskCategory`),
	- concrete tasks (`mluo:Task`),
	- hierarchical links via `skos:broader`.

## Source of concepts

- **Ontology metadata**: the project.
- **Modality concepts**: the project.
- **Task category concepts**: curated categories, with definitions sourced from IBM ML reference material (The 2026 Guide to Machine Learning).
- **Task concepts**: based on Hugging Face task vocabulary and descriptions (Hugging Face API).
- **Task examples** (`skos:example`): derived from task-related metadata (datasets, models, demos, libraries) on Hugging Face (Hugging Face API).

The 2026 Guide to Machine Learning : https://www.ibm.com/think/topics/machine-learning  \
Hugging Face API : https://www.huggingface.co/api/tasks

## Why this hierarchy

The hierarchy of the task categories is entirely sourced from IBM, but only task categories relevant to the task extrated from the Hugging face API are represented in this hierarchy. So, most of the task categories presented by the IBM guide are absent in this thesaurus.

For the distribution of the tasks in the hierarchy, there is two methods :
- link a task present in the Hugging Face API to a task name or description pattern:
	- name cue: keywords in the slug (`classification`, `segmentation`, `generation`, `question-answering`, etc.)
	- description cue: task objective, input/output modality, and evaluation setting (label prediction, generation, retrieval, control)
	- IBM backing: each placement is backed by the IBM guide
- place the task in the nearest category when there is no exact lexical match:
	- choose the category that best matches the primary objective and modality
	- if ambiguous, prioritize the category that improves dataset/model discovery