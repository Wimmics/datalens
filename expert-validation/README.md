# Expert Validation of Task--Sub-task Associations

This folder contains the material used to analyze the expert validation of inferred hierarchical associations between machine learning tasks and sub-tasks in the Datalens thesaurus.

The validation aimed to assess whether the inferred `skos:broader` relationships between sub-tasks and tasks were considered relevant by people familiar with machine learning resources and development workflows.

## Evaluation Protocol

We conducted an expert evaluation with IT researchers and developers. Participants were shown task--sub-task associations and asked to rate each association using a 5-point Likert scale reflecting their level of agreement:

- Not at all relevant
- Slightly relevant
- Somewhat relevant
- Very relevant
- Extremely relevant

For each association, participants were also asked to report their confidence using a 5-point Likert scale. They could additionally suggest alternative task associations for the given sub-task.

The evaluation was organized as two online questionnaires, each containing 32 task--sub-task associations. We collected 6 responses in total, with three responses for each questionnaire.

## Questionnaire Example

Each question followed the structure below:

```text
Sub-task: [sub-task name]
Proposed task: [task name]

How relevant is this task--sub-task association?
[5-point agreement scale]

How confident are you in your response?
[5-point confidence scale]

Would you suggest another task association?
[optional free-text answer]
```

## Participants

Participants reported varied familiarity with Hugging Face, ranging from somewhat familiar to extremely familiar. Half of the participants reported being moderately familiar with the platform.

Their reported usage frequency of Hugging Face varied:

- Everyday: 2 participants
- Once a week: 1 participant
- Once a month: 1 participant
- Once a year: 1 participant
- Less than once a year: 1 participant

Participants reported searching for datasets and models at different frequencies:

- Everyday: 1 participant
- Once a week: 3 participants
- Once a year: 2 participants

Regarding machine learning expertise, two participants identified themselves as ML experts, two reported an advanced level of expertise, one reported an intermediate level, and one reported a beginner level.

## Data

The [data/results.csv](data/results.csv) file contains the validation responses used for analysis and visualization.

The main columns are:

- `participant_id`: identifier of the participant within a questionnaire group
- `questionnaire_id`: questionnaire group identifier
- `task`: evaluated sub-task and proposed task association
- `reported agreement`: participant rating of the association relevance
- `reported confidence level`: participant confidence in the rating

## Scripts

### [charts.R](charts.R)

This R script reads [data/results.csv](data/results.csv), normalizes labels for visualization, converts agreement levels to ordered factors, and computes agreement scores for ordering task--sub-task associations.

It generates two charts in the [charts](charts/) folder:

- [agreement_task.png](charts/agreement_task.png): bar charts showing the agreement distribution for each task--sub-task association, separated by questionnaire group.
- [agreement_freq.png](charts/agreement_freq.png): frequency chart showing how often agreement levels co-occurred with different numbers of respondents.

The script uses the following R packages:

- `tidyverse`
- `scales`
- `ggpubr`
- `cowplot`

To run the script from this folder:

```sh
cd expert-validation
Rscript charts.R
```

## Outputs

The generated charts summarize the relevance ratings assigned by experts to the inferred task hierarchy:

- Agreement by association helps identify which inferred links were strongly supported or weakly supported.
- Agreement frequency helps inspect whether responses converged across participants or were more dispersed.
