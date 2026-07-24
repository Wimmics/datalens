import difflib
import re
import csv


def normalize_tag(tag):
    return re.sub(
        r"[^a-z0-9]",
        "",
        tag.lower()
    )


def generate_kaggle_hf_matches_csv(
    hf_file,
    kaggle_official_file,
    kaggle_occurrences_file,
    exact_output_csv,
    approx_output_csv,
    similarity_threshold=0.8
):

    # -------------------------
    # Chargement Hugging Face
    # -------------------------

    hf_tags = {}

    with open(hf_file, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            tag = parts[0].lower()
            count = int(parts[-1])

            hf_tags[tag] = count


    # -------------------------
    # Tags officiels Kaggle
    # -------------------------

    kaggle_official = {}

    with open(kaggle_official_file, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            parts = line.split("\t")

            if len(parts) == 2:

                kaggle_official[
                    parts[0].lower()
                ] = parts[1]


    # -------------------------
    # Occurrences Kaggle
    # -------------------------

    kaggle_stats = {}

    current_tag = None

    with open(kaggle_occurrences_file, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if line.startswith("Tag :"):

                current_tag = (
                    line.replace("Tag :", "")
                    .strip()
                    .lower()
                )

                kaggle_stats[current_tag] = {
                    "occurrence": 0,
                    "coverage": "0%"
                }


            elif line.startswith("Occurrence :"):

                kaggle_stats[current_tag]["occurrence"] = int(
                    line.replace("Occurrence :", "")
                    .strip()
                )


            elif line.startswith("Couverture :"):

                kaggle_stats[current_tag]["coverage"] = (
                    line.replace("Couverture :", "")
                    .strip()
                )


    # -------------------------
    # Préparation matching
    # -------------------------

    normalized_hf = {
        normalize_tag(tag): tag
        for tag in hf_tags
    }


    exact_rows = []
    approx_rows = []


    for kaggle_tag, stats in kaggle_stats.items():

        # Correspondance exacte

        if kaggle_tag in hf_tags:

            exact_rows.append(
                {
                    "tag_kaggle": kaggle_tag,
                    "officiel_kaggle": kaggle_tag in kaggle_official,
                    "chemin_kaggle": kaggle_official.get(
                        kaggle_tag,
                        ""
                    ),
                    "occurrence_kaggle": stats["occurrence"],
                    "couverture_kaggle": stats["coverage"],
                    "tag_huggingface": kaggle_tag,
                    "occurrence_huggingface": hf_tags[kaggle_tag]
                }
            )


        # Correspondance approximative

        norm_kaggle = normalize_tag(kaggle_tag)

        for norm_hf, hf_tag in normalized_hf.items():

            score = difflib.SequenceMatcher(
                None,
                norm_kaggle,
                norm_hf
            ).ratio()


            if score >= similarity_threshold:

                approx_rows.append(
                    {
                        "tag_kaggle": kaggle_tag,
                        "officiel_kaggle": kaggle_tag in kaggle_official,
                        "chemin_kaggle": kaggle_official.get(
                            kaggle_tag,
                            ""
                        ),
                        "occurrence_kaggle": stats["occurrence"],
                        "couverture_kaggle": stats["coverage"],
                        "tag_huggingface": hf_tag,
                        "occurrence_huggingface": hf_tags[hf_tag],
                        "similarite": round(score, 3)
                    }
                )


    # -------------------------
    # Ecriture CSV
    # -------------------------

    with open(
        exact_output_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=exact_rows[0].keys()
            if exact_rows else []
        )

        writer.writeheader()
        writer.writerows(exact_rows)


    with open(
        approx_output_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=approx_rows[0].keys()
            if approx_rows else []
        )

        writer.writeheader()
        writer.writerows(approx_rows)



# Exemple d'utilisation

generate_kaggle_hf_matches_csv(
    "kaggle_study/normalized_values_models.txt",
    "kaggle_study/tags.txt",
    "kaggle_study/stat/model_stats_tags.txt",
    "kaggle_study/stat/model_matching_exact.csv",
    "kaggle_study/stat/model_matching_approx.csv",
    similarity_threshold=0.8
)