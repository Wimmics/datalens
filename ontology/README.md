# MLUO Thesaurus

`datalens_th.ttl` is a SKOS thesaurus used to describe machine learning datasets and tasks with a controlled vocabulary.

## What the thesaurus contains

- An thesaurus header with metadata (title, creators, version, dates, license).
- A **Modality Scheme** (`datalens_th:ModalityScheme`) with concepts of modalities such as `Text`, `Image`, `Audio`, etc.
- A **Format Scheme** (`datalens_th:FormatScheme`) with concepts of formats such as `json`, `csv`, `parquet`, etc.
- A **Size Category Scheme** (`datalens_th:DatasetSizeScheme`) with concepts of size categories of a dataset (number of records such as `< 1K` or `100K - 1M`).
- A **Dataset Library Scheme** (`datalens_th:DatasetLibraryScheme`) with concepts of libraries for datasets such as `NeMo Data Designer`, `pandas`, `Datasets`, etc.
- A **Model Library Scheme** (`datalens_th:ModelLibraryScheme`) with concepts of libraries for models such as `PyTorch`, `Scikit-learn`, `Transformers`, etc.
- A **Task Scheme** (`datalens_th:TaskScheme`) with:
	- task categories (`datalens_o:TaskCategory`),
	- concrete tasks (`datalens_o:Task`),
	- hierarchical links via `skos:broader`.

## Source of concepts

- **Ontology metadata**: the project.
- **Modality concepts**: based on Hugging Face modalities.
- **Library concepts**: based on libraries used by Hugging Face (Hugging Face API).
- **Format concepts**: based on formats used by Hugging Face (Hugging Face API).
- **Size Ctegory concepts**: based on Hugging Face size categories (Hugging Face API).
- **Task category concepts**: curated categories, with definitions sourced from IBM ML reference material (The 2026 Guide to Machine Learning).
- **Task concepts**: based on Hugging Face task vocabulary and descriptions (Hugging Face API).
- **Task examples** (`skos:example`): derived from task-related metadata (datasets, models, demos, libraries) on Hugging Face (Hugging Face API).

The 2026 Guide to Machine Learning : https://www.ibm.com/think/topics/machine-learning  \
Hugging Face API : https://www.huggingface.co/api/tasks
https://huggingface.co/spaces/huggingface/openapi#tag/datasets/GET/api/datasets-tags-by-type
https://huggingface.co/spaces/huggingface/openapi#tag/models/GET/api/models-tags-by-type

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