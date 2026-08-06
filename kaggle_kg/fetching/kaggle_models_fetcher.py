#!/usr/bin/env python3
"""
kaggle_metakaggle_models_fetcher.py

Récupère les métadonnées utiles de TOUS les models publics Kaggle, en
passant par le dataset officiel "Meta Kaggle" (kaggle/meta-kaggle), et
produit UNE SEULE sortie.

Contrairement aux datasets, un Model a une structure à deux niveaux :
un Model peut avoir PLUSIEURS Variations (ex : qwen2.5 a 42 variations —
Transformers 0.5b, 1.5b...), et c'est au niveau de la VARIATION que
vivent le framework, la licence, la taille des fichiers, etc. (pas au
niveau du modèle). Faire "une ligne par modèle" perdrait donc cette
information, et "deux fichiers séparés" obligerait à refaire la jointure
soi-même. Ce script produit donc UNE ligne par VARIATION, avec toutes les
informations du modèle parent fusionnées dessus et un lien explicite
('ModelId') pour remonter au modèle.

Optimisation du téléchargement
-------------------------------
Comme pour le script datasets, on ne télécharge QUE les tables qui
apportent une information utile à ce niveau (une ligne par variation),
au lieu de tout fichier "Model*" (le schéma Meta Kaggle contient aussi
des tables annexes/volumineuses qui n'ajouteraient rien ici) :

  - Models.csv                table principale : compteurs agrégés
                               (vues, votes, téléchargements...).
  - ModelVersions.csv         dernière version DU MODÈLE : titre,
                               sous-titre, description, slug.
  - ModelVariations.csv       dimension variation : framework, slug de
                               variation, etc.
  - <table historique des versions de variation>
                               dernière version DE CHAQUE VARIATION :
                               licence, framework, taille des fichiers...
                               Le nom exact de cette table n'est pas figé
                               en dur (schéma Meta Kaggle pas garanti
                               stable) : elle est repérée dynamiquement
                               comme tout fichier dont le nom contient à
                               la fois "Variation" et "Version"
                               (typiquement ModelVariationVersions.csv).
  - ModelTags.csv / Tags.csv  tags du modèle, résolus en noms.
  - Users.csv / Organizations.csv / UserOrganizations.csv
                               propriétaire du modèle + son/ses
                               organisation(s).

Tables volontairement EXCLUES : tout fichier "Votes" (redondant : les
compteurs agrégés de votes vivent déjà dans Models.csv, comme pour
Datasets.csv), ainsi que toute autre table "Model*" non listée
ci-dessus (annexes, hors périmètre d'un catalogue modèle/variation).

Sortie
------
{out}.csv / {out}.json : une ligne par variation.
  - colonnes de ModelVariations.csv (telles quelles, dont "VariationId")
  - "Latest_*" : dernière version de la variation (licence, framework...)
  - "ModelId" : lien explicite vers le modèle parent
  - "Model_VariationCount" : nombre de variations de ce modèle
  - "Model_*" : toutes les infos du modèle parent (titre, description,
    tags, propriétaire "Model_Owner_*", organisation
    "Model_Organization_*", compteurs agrégés...)

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

METAKAGGLE_REF = "kaggle/meta-kaggle"

MAIN_TABLE = "Models.csv"
MAIN_KEY = "Id"
MODEL_FK = "ModelId"  # référence Models.Id dans ModelVersions/ModelVariations/ModelTags

VARIATION_TABLE = "ModelVariations.csv"
VARIATION_KEY = "Id"
VARIATION_FOREIGN_KEY_CANDIDATES = ("ModelVariationId", "VariationId")  # dans la table de versions de variation

# Tables au nom fixe et connu : chacune apporte une information qui n'existe
# nulle part ailleurs à ce niveau d'agrégation (voir docstring ci-dessus).
FIXED_RELEVANT_TABLES = [
    "Models.csv",
    "ModelVersions.csv",
    "ModelVariations.csv",
    "ModelTags.csv",
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


def filter_available(api, download_dir=None):
    """Détermine les fichiers à télécharger.

    La logique priorise les fichiers déjà présents localement dans le dossier de
    téléchargement. Si l’API Kaggle ne les expose pas, on s’appuie quand même
    sur le stockage local pour éviter l’échec total du flux.
    """
    log(f"Vérification des fichiers disponibles dans {METAKAGGLE_REF} ...")

    local_names = []
    if download_dir is not None:
        local_dir = Path(download_dir)
        if local_dir.exists():
            local_names = [p.name for p in local_dir.iterdir() if p.is_file() and p.suffix.lower() == ".csv"]

    api_names = set()
    try:
        file_list = api.dataset_list_files(METAKAGGLE_REF)
        api_names = {f.name for f in file_list.files}
    except Exception as exc:
        log(f"ATTENTION : impossible d'interroger l'API Kaggle ({exc}), fallback sur les fichiers locaux.")

    available_names = set(local_names) | api_names

    fixed = [n for n in FIXED_RELEVANT_TABLES if n in available_names]
    missing_fixed = [n for n in FIXED_RELEVANT_TABLES if n not in available_names]
    if missing_fixed:
        log(f"ATTENTION : absents du dataset Meta Kaggle actuel ou du cache local, ignorés : {missing_fixed}")

    variation_version_files = sorted(
        n for n in available_names
        if n.endswith(".csv") and "variation" in n.lower() and "version" in n.lower()
    )
    if not variation_version_files:
        log("ATTENTION : aucune table 'historique des versions de variation' trouvée (nom contenant "
            "'Variation' et 'Version') ; licence/framework par variation ne seront pas ajoutés.")
    elif len(variation_version_files) > 1:
        log(f"ATTENTION : plusieurs tables candidates pour l'historique des versions de variation "
            f"{variation_version_files}, seule la première sera utilisée.")

    available = sorted(set(fixed + variation_version_files))
    log(f"Tables à télécharger ({len(available)}) : {available}")
    return available, variation_version_files




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


def latest_by_group(df, group_col, order_col_candidates=("VersionNumber", "CreationDate")):
    order_col = next((c for c in order_col_candidates if c in df.columns), None)
    if order_col:
        df = df.sort_values(order_col)
    return df.drop_duplicates(group_col, keep="last")


def prefix_variation_version_columns(df, key_col):
    """Renomme les colonnes de version de variation en 'Version_*' pour expliciter
    qu'elles dépendent de la variation, pas du modèle parent."""
    version_columns = [
        "VariationOverview",
        "VariationUsage",
        "FineTunable",
        "SourceUrl",
        "SourceOrganizationName",
    ]
    rename_map = {}
    for col in version_columns:
        if col in df.columns:
            rename_map[col] = f"Version_{col}"
    if not rename_map:
        return df
    return df.rename(columns=rename_map)


# --- Niveau MODÈLE : reproduit le même enrichissement que pour les datasets ---

def merge_latest_model_version(main_df, files):
    if "ModelVersions.csv" not in files:
        log("ModelVersions.csv indisponible : titre/description de la dernière version du "
            "modèle ne seront pas ajoutés.")
        return main_df
    log("Fusion de la dernière version de chaque modèle (ModelVersions.csv) ...")
    versions = pd.read_csv(files["ModelVersions.csv"], low_memory=False)
    if MODEL_FK not in versions.columns:
        log(f"  -> pas de colonne '{MODEL_FK}' dans ModelVersions.csv, ignoré.")
        return main_df
    latest = latest_by_group(versions, MODEL_FK)
    latest = latest.add_prefix("Latest_").rename(columns={f"Latest_{MODEL_FK}": MODEL_FK})
    main_df = main_df.merge(latest, left_on=MAIN_KEY, right_on=MODEL_FK, how="left")
    main_df = main_df.drop(columns=[MODEL_FK])  # doublon exact de MAIN_KEY, inutile
    log(f"  -> {len(latest.columns) - 1} colonnes ajoutées (préfixe 'Latest_').")
    return main_df


def merge_model_tags(main_df, files):
    if "ModelTags.csv" not in files or "Tags.csv" not in files:
        log("ModelTags.csv et/ou Tags.csv indisponibles : pas de colonne 'Tags'.")
        return main_df
    log("Fusion des tags (ModelTags.csv + Tags.csv) ...")
    mtags = pd.read_csv(files["ModelTags.csv"], low_memory=False)
    tags = pd.read_csv(files["Tags.csv"], low_memory=False)
    if not {"TagId", MODEL_FK}.issubset(mtags.columns) or not {"Id", "Name"}.issubset(tags.columns):
        log("  -> colonnes attendues introuvables, tags ignorés.")
        return main_df
    mtags = mtags.merge(tags[["Id", "Name"]], left_on="TagId", right_on="Id", how="left")
    agg = (
        mtags.groupby(MODEL_FK)["Name"]
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


def build_models_table(files):
    """Une ligne par MODÈLE, enrichie (titre, tags, propriétaire, organisation)."""
    if MAIN_TABLE not in files:
        sys.exit(f"{MAIN_TABLE} n'a pas pu être récupéré : impossible de continuer.")
    log(f"Chargement de {MAIN_TABLE} ...")
    models_df = pd.read_csv(files[MAIN_TABLE], low_memory=False)

    models_df = merge_latest_model_version(models_df, files)
    models_df = merge_model_tags(models_df, files)
    models_df = merge_owner(models_df, files)
    models_df = merge_owning_organization(models_df, files)

    return models_df


# --- Niveau VARIATION ---

def build_variations_table(files, variation_version_files):
    """Une ligne par VARIATION, avec sa dernière version fusionnée (licence, framework...)."""
    if VARIATION_TABLE not in files:
        sys.exit(f"{VARIATION_TABLE} n'a pas pu être récupéré : impossible de continuer.")
    log(f"Chargement de {VARIATION_TABLE} ...")
    variations = pd.read_csv(files[VARIATION_TABLE], low_memory=False)
    if VARIATION_KEY not in variations.columns:
        sys.exit(f"{VARIATION_TABLE} ne contient pas de colonne '{VARIATION_KEY}'.")
    variations = variations.rename(columns={VARIATION_KEY: "VariationId"})

    version_file = next((f for f in variation_version_files if f in files), None)
    if version_file is None:
        log("Pas d'historique des versions de variation disponible : licence/framework de la "
            "dernière version ne seront pas ajoutés.")
        return variations

    log(f"Fusion de la dernière version de chaque variation ({version_file}) ...")
    versions = pd.read_csv(files[version_file], low_memory=False)
    key_col = next((c for c in VARIATION_FOREIGN_KEY_CANDIDATES if c in versions.columns), None)
    if not key_col:
        log(f"  -> aucune colonne de clé de variation reconnue dans {version_file}, ignoré.")
        return variations

    latest = latest_by_group(versions, key_col)
    latest = prefix_variation_version_columns(latest, key_col)
    variations = variations.merge(latest, left_on="VariationId", right_on=key_col, how="left")
    if key_col != "VariationId":
        variations = variations.drop(columns=[key_col])  # doublon exact de VariationId, inutile
    added_columns = [c for c in latest.columns if c != key_col]
    log(f"  -> {len(added_columns)} colonnes ajoutées ({', '.join(added_columns[:5])}{'...' if len(added_columns) > 5 else ''}).")
    return variations


def add_variation_counts(variations_df):
    if MODEL_FK not in variations_df.columns:
        return variations_df
    counts = variations_df.groupby(MODEL_FK).size().rename("Model_VariationCount")
    return variations_df.merge(counts, left_on=MODEL_FK, right_index=True, how="left")


def merge_model_info(variations_df, models_df):
    """Fusionne les infos du modèle parent sur chaque ligne de variation, avec un lien
    explicite ('ModelId') et toutes les autres colonnes du modèle préfixées 'Model_'."""
    if MODEL_FK not in variations_df.columns:
        log(f"ATTENTION : pas de colonne '{MODEL_FK}' dans les variations, impossible de relier "
            f"au modèle parent.")
        return variations_df
    models_renamed = models_df.rename(columns={MAIN_KEY: MODEL_FK})
    models_prefixed = models_renamed.rename(
        columns={c: f"Model_{c}" for c in models_renamed.columns if c != MODEL_FK}
    )
    merged = variations_df.merge(models_prefixed, on=MODEL_FK, how="left")
    log(f"Informations du modèle parent fusionnées sur chaque variation "
        f"(lien via '{MODEL_FK}', préfixe 'Model_').")
    return merged


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
        description="Récupère les métadonnées utiles de tous les models Kaggle via Meta Kaggle "
                     "(une seule sortie : une ligne par variation, avec le modèle parent fusionné)."
    )
    parser.add_argument("--out", default="all_models", help="Préfixe du fichier de sortie")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--download-dir", default="./meta_kaggle_raw",
                         help="Dossier où stocker les CSV Meta Kaggle bruts (réutilisés si déjà présents)")
    args = parser.parse_args()

    api = get_api()
    filenames, variation_version_files = filter_available(api, args.download_dir)
    files = download_files(api, filenames, Path(args.download_dir))

    models_df = build_models_table(files)
    variations_df = build_variations_table(files, variation_version_files)
    variations_df = add_variation_counts(variations_df)
    result = merge_model_info(variations_df, models_df)

    log(f"\nTotal variations : {len(result)} lignes, {len(result.columns)} colonnes de métadonnées "
        f"({result[MODEL_FK].nunique() if MODEL_FK in result.columns else '?'} modèles distincts).")
    save_output(result, args.out, args.format)


if __name__ == "__main__":
    main()
