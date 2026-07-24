#!/usr/bin/env python3
"""
kaggle_metakaggle_models_fetcher.py

Récupère les métadonnées EXACTES et EXHAUSTIVES de tous les models publics
Kaggle via le dataset officiel "Meta Kaggle" (kaggle/meta-kaggle), en
uniformisant avec le script équivalent pour les datasets.

Depuis janvier 2025, Meta Kaggle inclut ces tables dédiées aux models
(annonce officielle Kaggle) :
  - Models.csv               : un modèle = une entrée (ex: "qwen-lm/qwen2.5")
  - ModelVariations.csv      : les variations d'un modèle (ex: "transformers-0.5b")
  - ModelVariationVersions.csv : les versions de chaque variation (licence,
                                 framework, date de création, etc.)
  - ModelVersions.csv        : versions au niveau du modèle
  - ModelTags.csv            : tags associés à chaque modèle
  - ModelVotes.csv           : votes par modèle

Point important sur la structure : un Model peut avoir PLUSIEURS Variations
(ex: qwen2.5 a 42 variations : Transformers - 0.5b, Transformers - 0.5b-instruct,
etc.). Ce script produit donc DEUX fichiers de sortie :
  1. {out}.csv/json          : une ligne par MODEL (vue d'ensemble, avec nombre
                               de variations, tags, propriétaire, etc.)
  2. {out}_variations.csv/json : une ligne par VARIATION x dernière VERSION
                               (avec licence, framework, etc., puisque ces
                               informations vivent à ce niveau, pas au niveau
                               du modèle — comme pour DatasetVersions côté
                               datasets).

Pré-requis
----------
1. pip install -U kaggle pandas
2. ~/.kaggle/kaggle.json (chmod 600) ou KAGGLE_USERNAME / KAGGLE_KEY

Utilisation
-----------
python kaggle_metakaggle_models_fetcher.py --out all_models
"""

import argparse
import sys
from pathlib import Path

try:
    import pandas as pd
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    sys.exit(
        "Dépendances manquantes.\n"
        "Installe-les avec : pip install -U kaggle pandas"
    )

METAKAGGLE_REF = "kaggle/meta-kaggle"

# Schéma confirmé par l'équipe Kaggle (annonce du 6 janvier 2025 sur la page
# de discussion de Meta Kaggle). Le script continue même si l'un de ces
# fichiers est absent ou renommé : il log un avertissement et poursuit avec
# ce qu'il a pu récupérer, plutôt que de planter.
FILES_NEEDED = [
    "Models.csv",
    "ModelVariations.csv",
    "ModelVariationVersions.csv",
    "ModelVersions.csv",
    "ModelTags.csv",
    "ModelVotes.csv",
    "Tags.csv",   # table partagée avec les datasets, déjà utilisée pour les noms de tags
    "Users.csv",  # table partagée, pour retrouver le nom du propriétaire
]


def log(msg):
    print(msg, flush=True)


def get_api():
    api = KaggleApi()
    try:
        api.authenticate()
    except Exception as e:
        sys.exit(
            f"Échec de l'authentification Kaggle : {e}\n"
            "Vérifie ~/.kaggle/kaggle.json (chmod 600) ou KAGGLE_USERNAME/KAGGLE_KEY."
        )
    return api


def download_files(api, filenames, download_dir):
    download_dir.mkdir(parents=True, exist_ok=True)
    available = {}
    for fname in filenames:
        target = download_dir / fname
        if target.exists():
            log(f"[meta-kaggle] {fname} déjà téléchargé, on réutilise.")
            available[fname] = target
            continue
        try:
            log(f"[meta-kaggle] Téléchargement de {fname} ...")
            api.dataset_download_file(
                METAKAGGLE_REF, fname, path=str(download_dir), force=False, quiet=False
            )
            zip_path = download_dir / f"{fname}.zip"
            if zip_path.exists():
                import zipfile
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(download_dir)
                zip_path.unlink()
            if target.exists():
                available[fname] = target
                log(f"[meta-kaggle] OK : {fname}")
            else:
                log(f"[meta-kaggle] ATTENTION : {fname} introuvable après téléchargement, ignoré.")
        except Exception as e:
            log(f"[meta-kaggle] ATTENTION : impossible de télécharger {fname} ({e}), ignoré.")
    return available


def build_models_overview(files):
    """Une ligne par model : titre, propriétaire, tags, nombre de variations, stats."""
    if "Models.csv" not in files:
        sys.exit("Models.csv n'a pas pu être récupéré : impossible de continuer.")

    log("Chargement de Models.csv ...")
    models = pd.read_csv(files["Models.csv"], low_memory=False)

    if "ModelVariations.csv" in files:
        log("Chargement de ModelVariations.csv (comptage des variations par modèle) ...")
        variations = pd.read_csv(files["ModelVariations.csv"], low_memory=False)
        if "ModelId" in variations.columns:
            variation_counts = variations.groupby("ModelId").size().rename("VariationCount")
            models = models.merge(variation_counts, left_on="Id", right_index=True, how="left")
            models["VariationCount"] = models["VariationCount"].fillna(0).astype(int)

    if "ModelTags.csv" in files and "Tags.csv" in files:
        log("Chargement de ModelTags.csv / Tags.csv (tags par modèle) ...")
        mtags = pd.read_csv(files["ModelTags.csv"], low_memory=False)
        tags = pd.read_csv(files["Tags.csv"], low_memory=False)
        if "TagId" in mtags.columns and "Id" in tags.columns and "Name" in tags.columns:
            mtags = mtags.merge(tags[["Id", "Name"]], left_on="TagId", right_on="Id", how="left")
            key_col = "ModelId" if "ModelId" in mtags.columns else None
            if key_col:
                tags_by_model = (
                    mtags.groupby(key_col)["Name"]
                    .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
                    .rename("Tags")
                )
                models = models.merge(tags_by_model, left_on="Id", right_index=True, how="left")

    if "ModelVotes.csv" in files:
        log("Chargement de ModelVotes.csv (comptage des votes par modèle) ...")
        votes = pd.read_csv(files["ModelVotes.csv"], low_memory=False)
        key_col = "ModelId" if "ModelId" in votes.columns else None
        if key_col:
            vote_counts = votes.groupby(key_col).size().rename("VoteCount")
            models = models.merge(vote_counts, left_on="Id", right_index=True, how="left")
            models["VoteCount"] = models["VoteCount"].fillna(0).astype(int)

    owner_col = next((c for c in ("OwnerUserId", "CreatorUserId") if c in models.columns), None)
    if "Users.csv" in files and owner_col:
        log(f"Chargement de Users.csv (nom du propriétaire, via {owner_col}) ...")
        users = pd.read_csv(files["Users.csv"], low_memory=False)
        if "Id" in users.columns and "UserName" in users.columns:
            users = users[["Id", "UserName", "DisplayName"]].add_prefix("Owner_")
            models = models.merge(users, left_on=owner_col, right_on="Owner_Id", how="left")

    return models


def build_variations_detail(files):
    """Une ligne par variation x dernière version : framework, licence, etc."""
    if "ModelVariations.csv" not in files:
        log("ModelVariations.csv absent : pas de fichier détail des variations généré.")
        return None

    log("Chargement de ModelVariations.csv ...")
    variations = pd.read_csv(files["ModelVariations.csv"], low_memory=False)

    if "ModelVariationVersions.csv" in files:
        log("Chargement de ModelVariationVersions.csv (dernière version par variation) ...")
        versions = pd.read_csv(files["ModelVariationVersions.csv"], low_memory=False)
        key_col = next((c for c in ("ModelVariationId", "VariationId") if c in versions.columns), None)
        if key_col:
            if "VersionNumber" in versions.columns:
                versions = versions.sort_values("VersionNumber").drop_duplicates(key_col, keep="last")
            else:
                versions = versions.drop_duplicates(key_col, keep="last")
            versions = versions.add_prefix("Version_")
            variations = variations.merge(
                versions, left_on="Id", right_on=f"Version_{key_col}", how="left"
            )

    return variations


def save_outputs(df, out_base, fmt, label):
    if df is None or df.empty:
        log(f"Rien à sauvegarder pour {label}.")
        return
    if fmt in ("csv", "both"):
        csv_path = Path(out_base).with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        log(f"-> CSV ({label}) : {csv_path} ({len(df)} lignes)")
    if fmt in ("json", "both"):
        json_path = Path(out_base).with_suffix(".json")
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        log(f"-> JSON ({label}) : {json_path} ({len(df)} entrées)")


def main():
    parser = argparse.ArgumentParser(
        description="Récupère les métadonnées exhaustives de tous les models Kaggle via Meta Kaggle"
    )
    parser.add_argument("--out", default="all_models", help="Préfixe des fichiers de sortie")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--download-dir", default="./meta_kaggle_raw",
                         help="Dossier où stocker les CSV Meta Kaggle bruts (réutilisés si déjà présents)")
    parser.add_argument("--skip-variations", action="store_true",
                         help="Ne génère que la vue d'ensemble par modèle, sans le détail des variations")
    args = parser.parse_args()

    api = get_api()
    files = download_files(api, FILES_NEEDED, Path(args.download_dir))

    overview = build_models_overview(files)
    log(f"Total models (table Meta Kaggle) : {len(overview)}")
    save_outputs(overview, args.out, args.format, label="models")

    if not args.skip_variations:
        variations = build_variations_detail(files)
        if variations is not None:
            log(f"Total variations de modèles : {len(variations)}")
            save_outputs(variations, f"{args.out}_variations", args.format, label="variations")


if __name__ == "__main__":
    main()