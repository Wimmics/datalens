#!/usr/bin/env python3
"""
kaggle_metakaggle_datasets_fetcher.py

Récupère les métadonnées EXACTES et EXHAUSTIVES de tous les datasets publics
Kaggle en passant par le dataset officiel "Meta Kaggle" (kaggle/meta-kaggle),
plutôt que par l'endpoint de listing de l'API (datasets/list), qui est
volontairement bridé côté serveur :
  - sans terme de recherche -> résultats vides / tronqués
  - avec terme de recherche -> plafond dur d'environ 10 000 résultats
    (~500 pages), confirmé par l'équipe Kaggle elle-même, qui recommande
    justement d'utiliser Meta Kaggle pour ce cas d'usage.
    Source : https://github.com/Kaggle/kaggle-api/issues/553

Meta Kaggle est un dataset mis à jour régulièrement par Kaggle et contenant
des tables CSV normalisées (Datasets, DatasetVersions, DatasetTags, Tags,
Users...). Ce script télécharge uniquement les fichiers nécessaires (pas
tout le bundle Meta Kaggle, qui est volumineux) et les assemble en une seule
table de métadonnées par dataset.

Pré-requis
----------
1. pip install -U kaggle pandas
2. ~/.kaggle/kaggle.json (chmod 600) ou KAGGLE_USERNAME / KAGGLE_KEY

Utilisation
-----------
python kaggle_metakaggle_datasets_fetcher.py --out all_datasets

Note sur la fraîcheur des données : Meta Kaggle est généralement mis à jour
quotidiennement par Kaggle, donc les datasets créés dans les toutes
dernières heures peuvent ne pas encore y figurer.
"""

import argparse
import json
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

# Fichiers Meta Kaggle nécessaires. Le script continue même si l'un d'eux
# est absent ou renommé (le schéma peut évoluer) : il log un avertissement
# et poursuit avec ce qu'il a pu récupérer.
FILES_NEEDED = [
    "Datasets.csv",
    "DatasetVersions.csv",
    "DatasetTags.csv",
    "Tags.csv",
    "Users.csv",
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


def download_metakaggle_files(api, download_dir):
    download_dir.mkdir(parents=True, exist_ok=True)
    available = {}
    for fname in FILES_NEEDED:
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
            # Le fichier peut arriver zippé (fname + ".zip") -> on le dézippe.
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


def build_dataset_table(files):
    if "Datasets.csv" not in files:
        sys.exit("Datasets.csv n'a pas pu être récupéré : impossible de continuer.")

    log("Chargement de Datasets.csv ...")
    datasets = pd.read_csv(files["Datasets.csv"], low_memory=False)

    if "DatasetVersions.csv" in files:
        log("Chargement de DatasetVersions.csv (dernière version par dataset) ...")
        versions = pd.read_csv(files["DatasetVersions.csv"], low_memory=False)
        # On garde uniquement la version la plus récente de chaque dataset
        if "DatasetId" in versions.columns and "VersionNumber" in versions.columns:
            versions = versions.sort_values("VersionNumber").drop_duplicates("DatasetId", keep="last")
        elif "DatasetId" in versions.columns:
            versions = versions.drop_duplicates("DatasetId", keep="last")
        versions = versions.add_prefix("Version_")
        datasets = datasets.merge(
            versions, left_on="Id", right_on="Version_DatasetId", how="left"
        )

    if "DatasetTags.csv" in files and "Tags.csv" in files:
        log("Chargement de DatasetTags.csv / Tags.csv (tags par dataset) ...")
        dtags = pd.read_csv(files["DatasetTags.csv"], low_memory=False)
        tags = pd.read_csv(files["Tags.csv"], low_memory=False)
        if "TagId" in dtags.columns and "Id" in tags.columns and "Name" in tags.columns:
            dtags = dtags.merge(tags[["Id", "Name"]], left_on="TagId", right_on="Id", how="left")
            tags_by_dataset = (
                dtags.groupby("DatasetId")["Name"]
                .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
                .rename("Tags")
            )
            datasets = datasets.merge(tags_by_dataset, left_on="Id", right_index=True, how="left")

    if "Users.csv" in files and "OwnerUserId" in datasets.columns:
        log("Chargement de Users.csv (nom du propriétaire) ...")
        users = pd.read_csv(files["Users.csv"], low_memory=False)
        if "Id" in users.columns and "UserName" in users.columns:
            users = users[["Id", "UserName", "DisplayName"]].add_prefix("Owner_")
            datasets = datasets.merge(
                users, left_on="OwnerUserId", right_on="Owner_Id", how="left"
            )

    return datasets


def save_outputs(df, out_base, fmt):
    if fmt in ("csv", "both"):
        csv_path = Path(out_base).with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        log(f"-> CSV : {csv_path} ({len(df)} lignes)")
    if fmt in ("json", "both"):
        json_path = Path(out_base).with_suffix(".json")
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        log(f"-> JSON : {json_path} ({len(df)} entrées)")


def main():
    parser = argparse.ArgumentParser(
        description="Récupère les métadonnées exhaustives de tous les datasets Kaggle via Meta Kaggle"
    )
    parser.add_argument("--out", default="all_datasets", help="Préfixe des fichiers de sortie")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--download-dir", default="./meta_kaggle_raw",
                         help="Dossier où stocker les CSV Meta Kaggle bruts (réutilisés si déjà présents)")
    args = parser.parse_args()

    api = get_api()
    files = download_metakaggle_files(api, Path(args.download_dir))
    df = build_dataset_table(files)

    log(f"Total datasets (table Meta Kaggle) : {len(df)}")
    save_outputs(df, args.out, args.format)


if __name__ == "__main__":
    main()
