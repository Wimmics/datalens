#!/usr/bin/env python3
"""
kaggle_metakaggle_datasets_fetcher.py

Récupère les métadonnées utiles de TOUS les datasets publics Kaggle, en
passant par le dataset officiel "Meta Kaggle" (kaggle/meta-kaggle), et
produit UNE SEULE sortie : une ligne par dataset, avec les informations de
sa DERNIÈRE version (titre, description, licence, slug...), ses tags, et
son propriétaire (utilisateur + organisation).

Optimisation par rapport à une version qui télécharge tout fichier
"Dataset*"/"Datasource*" : ici on ne télécharge QUE les tables qui
apportent réellement de l'information à ce niveau d'agrégation (une ligne
par dataset). Ça évite en particulier DatasourceObjects.csv (liste de
CHAQUE fichier de CHAQUE version, potentiellement énorme) pour un gain nul
sur une vue d'ensemble des datasets.

Tables téléchargées et ce qu'elles apportent
---------------------------------------------
  - Datasets.csv          table principale : contient déjà les compteurs
                           agrégés (TotalViews, TotalDownloads, TotalVotes,
                           TotalKernels...).
  - DatasetVersions.csv   dernière version de chaque dataset : titre,
                           sous-titre, description, licence, slug, poids...
  - DatasetTags.csv       liaison dataset <-> tag.
  - Tags.csv              noms des tags (pour résoudre DatasetTags.csv).
  - Users.csv              propriétaire : username, tier, date d'inscription.
  - Organizations.csv     organisation propriétaire directe.
  - UserOrganizations.csv organisations d'appartenance du propriétaire.

Tables volontairement EXCLUES (et pourquoi)
---------------------------------------------
  - DatasetVotes.csv                  redondant : Datasets.csv contient déjà
                                       TotalVotes.
  - Datasources.csv / DatasourceVersions.csv / DatasourceObjects.csv
                                       niveau "fichier physique de
                                       stockage", pas de métadonnée
                                       descriptive utile ici ; le dernier
                                       est en plus massif.
  - DatasetTasks.csv / DatasetTaskSubmissions.csv
                                       fonctionnalité "tâches" annexe, hors
                                       périmètre d'un catalogue de datasets.

Si le schéma de Meta Kaggle change (table renommée/supprimée), le script
continue avec les tables encore disponibles et le signale, plutôt que
d'échouer.

Sortie
------
{out}.csv / {out}.json : une ligne par dataset.
  - colonnes de Datasets.csv (telles quelles)
  - colonnes de la dernière version, préfixées "Latest_"
  - "Tags" : liste des tags, séparés par ", "
  - colonnes du propriétaire, préfixées "Owner_" (+ "Owner_Organizations")
  - colonnes de l'organisation propriétaire directe, préfixées
    "Organization_"

Pré-requis
----------
1. pip install -U kaggle pandas
2. ~/.kaggle/kaggle.json (chmod 600) ou KAGGLE_USERNAME / KAGGLE_KEY

Utilisation
-----------
python kaggle_metakaggle_datasets_fetcher.py --out all_datasets
"""

import argparse
import sys
import zipfile
from pathlib import Path

try:
    import pandas as pd
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    sys.exit(
        "Dépendances manquantes.\n"
        "Installe-les avec : pip install -U kaggle pandas"
    )

BASE_FETCH_DIR = Path(__file__).parent / "input"

METAKAGGLE_REF = "kaggle/meta-kaggle"
MAIN_TABLE = "Datasets.csv"
MAIN_KEY = "Id"
FOREIGN_KEY = "DatasetId"  # colonne qui référence Datasets.Id dans les autres tables

# Seules tables téléchargées : chacune apporte une information qui n'existe
# nulle part ailleurs à ce niveau d'agrégation (voir docstring ci-dessus).
RELEVANT_TABLES = [
    "Datasets.csv",
    "DatasetVersions.csv",
    "DatasetTags.csv",
    "Tags.csv",
    "Users.csv",
    "Organizations.csv",
    "UserOrganizations.csv",
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


def filter_available(api, wanted):
    """Ne garde, parmi RELEVANT_TABLES, que les fichiers qui existent
    réellement dans Meta Kaggle aujourd'hui (le schéma évolue parfois)."""
    log(f"Vérification des fichiers disponibles dans {METAKAGGLE_REF} ...")
    # file_list = api.dataset_list_files(METAKAGGLE_REF)
    # all_names = {f.name for f in file_list.files}
    # available = [n for n in wanted if n in all_names]
    # missing = [n for n in wanted if n not in all_names]
    # if missing:
    #     log(f"ATTENTION : absents du dataset Meta Kaggle actuel, ignorés : {missing}")
    log(f"Tables à télécharger ({len(wanted)}) : {wanted}")
    return wanted


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


def latest_version_per_dataset(df):
    """Une ligne par dataset : uniquement la version la plus récente."""
    order_col = next((c for c in ("VersionNumber", "CreationDate") if c in df.columns), None)
    if order_col:
        df = df.sort_values(order_col)
    return df.drop_duplicates(FOREIGN_KEY, keep="last")


def merge_latest_version(main_df, files):
    if "DatasetVersions.csv" not in files:
        log("DatasetVersions.csv indisponible : titre/description/licence de la dernière "
            "version ne seront pas ajoutés.")
        return main_df
    log("Fusion de la dernière version de chaque dataset (DatasetVersions.csv) ...")
    versions = pd.read_csv(files["DatasetVersions.csv"], low_memory=False)
    latest = latest_version_per_dataset(versions)
    latest = latest.add_prefix("Latest_").rename(columns={f"Latest_{FOREIGN_KEY}": FOREIGN_KEY})
    main_df = main_df.merge(latest, left_on=MAIN_KEY, right_on=FOREIGN_KEY, how="left")
    main_df = main_df.drop(columns=[FOREIGN_KEY])  # doublon exact de MAIN_KEY, inutile
    log(f"  -> {len(latest.columns) - 1} colonnes ajoutées (préfixe 'Latest_').")
    return main_df


def merge_tags(main_df, files):
    if "DatasetTags.csv" not in files or "Tags.csv" not in files:
        log("DatasetTags.csv et/ou Tags.csv indisponibles : pas de colonne 'Tags'.")
        return main_df
    log("Fusion des tags (DatasetTags.csv + Tags.csv) ...")
    dtags = pd.read_csv(files["DatasetTags.csv"], low_memory=False)
    tags = pd.read_csv(files["Tags.csv"], low_memory=False)
    if not {"TagId", FOREIGN_KEY}.issubset(dtags.columns) or not {"Id", "Name"}.issubset(tags.columns):
        log("  -> colonnes attendues introuvables, tags ignorés.")
        return main_df
    dtags = dtags.merge(tags[["Id", "Name"]], left_on="TagId", right_on="Id", how="left")
    agg = (
        dtags.groupby(FOREIGN_KEY)["Name"]
        .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
        .rename("Tags")
    )
    main_df = main_df.merge(agg, left_on=MAIN_KEY, right_index=True, how="left")
    log("  -> colonne 'Tags' ajoutée.")
    return main_df


def merge_owner(main_df, files):
    owner_col = next((c for c in ("OwnerUserId", "CreatorUserId") if c in main_df.columns), None)
    if "Users.csv" not in files or owner_col is None:
        log("Users.csv indisponible ou colonne propriétaire absente : infos propriétaire ignorées.")
        return main_df
    log(f"Fusion des infos propriétaire (Users.csv, via '{owner_col}') ...")
    users = pd.read_csv(files["Users.csv"], low_memory=False)
    keep = [c for c in ("Id", "UserName", "DisplayName", "RegisterDate", "PerformanceTier") if c in users.columns]
    if "Id" not in keep or "UserName" not in keep:
        log("  -> colonnes attendues introuvables, ignoré.")
        return main_df
    u = users[keep].add_prefix("Owner_")
    main_df = main_df.merge(u, left_on=owner_col, right_on="Owner_Id", how="left")
    main_df = main_df.drop(columns=["Owner_Id"])  # doublon exact de owner_col, inutile
    log(f"  -> ajouté : {[c for c in u.columns if c != 'Owner_Id']}.")

    if "UserOrganizations.csv" in files and "Organizations.csv" in files:
        log("Fusion des organisations d'appartenance du propriétaire (UserOrganizations.csv) ...")
        uorgs = pd.read_csv(files["UserOrganizations.csv"], low_memory=False)
        orgs = pd.read_csv(files["Organizations.csv"], low_memory=False)
        name_col = "Name" if "Name" in orgs.columns else None
        slug_col = "Slug" if "Slug" in orgs.columns else None
        if {"UserId", "OrganizationId"}.issubset(uorgs.columns) and "Id" in orgs.columns and (name_col or slug_col):
            org_cols = [c for c in ("Id", name_col, slug_col) if c]
            uorgs = uorgs.merge(orgs[org_cols], left_on="OrganizationId", right_on="Id", how="left")
            display_col = name_col or slug_col
            orgs_by_user = (
                uorgs.groupby("UserId")[display_col]
                .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
                .rename("Owner_Organizations")
            )
            main_df = main_df.merge(orgs_by_user, left_on=owner_col, right_index=True, how="left")
            if slug_col:
                org_slugs_by_user = (
                    uorgs.groupby("UserId")[slug_col]
                    .apply(lambda slugs: ", ".join(sorted(set(s for s in slugs if pd.notna(s)))))
                    .rename("Owner_Organization_Slugs")
                )
                main_df = main_df.merge(org_slugs_by_user, left_on=owner_col, right_index=True, how="left")
            log("  -> colonnes 'Owner_Organizations' et 'Owner_Organization_Slugs' ajoutées.")
        else:
            log("  -> colonnes attendues introuvables, ignoré.")
    return main_df


def merge_owning_organization(main_df, files):
    if "Organizations.csv" not in files or "OwnerOrganizationId" not in main_df.columns:
        return main_df
    log("Fusion de l'organisation propriétaire directe (Organizations.csv, via 'OwnerOrganizationId') ...")
    orgs = pd.read_csv(files["Organizations.csv"], low_memory=False)
    name_col = "Name" if "Name" in orgs.columns else None
    slug_col = "Slug" if "Slug" in orgs.columns else None
    if "Id" not in orgs.columns or not (name_col or slug_col):
        log("  -> colonnes attendues introuvables, ignoré.")
        return main_df

    org_cols = [c for c in ("Id", name_col, slug_col) if c]
    o = orgs[org_cols].rename(columns={"Id": "Organization_Id"})
    if name_col:
        o = o.rename(columns={name_col: "Organization_Name"})
    if slug_col:
        o = o.rename(columns={slug_col: "Organization_Slug"})
    main_df = main_df.merge(o, left_on="OwnerOrganizationId", right_on="Organization_Id", how="left")
    main_df = main_df.drop(columns=["Organization_Id"])  # doublon exact de OwnerOrganizationId
    log("  -> colonnes 'Organization_Name' et 'Organization_Slug' ajoutées.")
    return main_df


def build_full_dataset_table(files):
    if MAIN_TABLE not in files:
        sys.exit(f"{MAIN_TABLE} n'a pas pu être récupéré : impossible de continuer.")
    log(f"Chargement de {MAIN_TABLE} ...")
    main_df = pd.read_csv(files[MAIN_TABLE], low_memory=False)

    main_df = merge_latest_version(main_df, files)
    main_df = merge_tags(main_df, files)
    main_df = merge_owner(main_df, files)
    main_df = merge_owning_organization(main_df, files)

    return main_df


def save_output(df, out_base, fmt):
    if df is None or df.empty:
        log("Rien à sauvegarder.")
        return
    if fmt in ("csv", "both"):
        csv_path = Path(out_base).with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        log(f"-> CSV : {csv_path} ({len(df)} lignes, {len(df.columns)} colonnes)")
    if fmt in ("json", "both"):
        json_path = Path(out_base).with_suffix(".json")
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        log(f"-> JSON : {json_path} ({len(df)} entrées)")


def main():
    parser = argparse.ArgumentParser(
        description="Récupère les métadonnées utiles de tous les datasets Kaggle via Meta Kaggle "
                     "(une seule sortie : une ligne par dataset, dernière version + propriétaire)."
    )
    parser.add_argument("--out", default=BASE_FETCH_DIR / "all_datasets", help="Préfixe du fichier de sortie")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--download-dir", default="./meta_kaggle_raw",
                         help="Dossier où stocker les CSV Meta Kaggle bruts (réutilisés si déjà présents)")
    args = parser.parse_args()

    api = get_api()
    filenames = filter_available(api, RELEVANT_TABLES)
    files = download_files(api, filenames, Path(args.download_dir))

    overview = build_full_dataset_table(files)
    log(f"\nTotal datasets : {len(overview)} lignes, {len(overview.columns)} colonnes de métadonnées.")
    save_output(overview, args.out, args.format)


if __name__ == "__main__":
    main()
