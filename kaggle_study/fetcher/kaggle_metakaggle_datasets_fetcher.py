#!/usr/bin/env python3
"""
kaggle_metakaggle_datasets_fetcher.py

Récupère TOUTES les métadonnées disponibles pour TOUS les datasets publics
Kaggle, en passant par le dataset officiel "Meta Kaggle" (kaggle/meta-kaggle).

Contrairement à une version qui ne prendrait qu'une liste figée de tables,
ce script DÉCOUVRE dynamiquement tous les fichiers Meta Kaggle pertinents
(tout fichier dont le nom commence par "Dataset" ou "Datasource", plus les
tables de référence partagées Tags/Users/Organizations/UserOrganizations),
les télécharge tous, et fusionne tout ce qui peut raisonnablement être mis
à plat.

Sorties produites
------------------
1. {out}.csv/json
   Une ligne par dataset : tous les champs de Datasets.csv + la dernière
   version (titre, description, licence, taille...) + tags + propriétaire +
   compteurs agrégés (votes, etc. si présents).

2. {out}_versions.csv/json
   L'historique COMPLET de toutes les versions de tous les datasets (pas
   seulement la dernière), pour ne rien perdre.

3. {out}_<table>.csv (copie brute)
   Tout fichier découvert qui n'a pas pu être fusionné proprement (relation
   ambiguë) est conservé tel quel dans le dossier de téléchargement, avec un
   message clair, pour que tu puisses l'exploiter toi-même si besoin.

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
MAIN_TABLE = "Datasets.csv"
MAIN_KEY = "Id"
FOREIGN_KEY = "DatasetId"  # nom de la colonne qui référence Datasets.Id dans les autres tables
FILE_PREFIXES = ["Dataset", "Datasource"]  # tout fichier commençant par l'un de ces préfixes est inclus
LOOKUP_TABLES = ["Tags.csv", "Users.csv", "Organizations.csv", "UserOrganizations.csv"]  # tables de référence partagées


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


def discover_files(api):
    log(f"Récupération de la liste réelle des fichiers de {METAKAGGLE_REF} ...")
    file_list = api.dataset_list_files(METAKAGGLE_REF)
    all_names = [f.name for f in file_list.files]
    log(f"{len(all_names)} fichiers trouvés dans Meta Kaggle au total.")

    matched = sorted(set(
        [n for n in all_names if any(n.startswith(p) for p in FILE_PREFIXES)]
        + [n for n in LOOKUP_TABLES if n in all_names]
    ))
    log(f"Fichiers retenus pour les datasets ({len(matched)}) : {matched}")
    return matched, all_names


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


def latest_by_group(df, group_col, order_col_candidates=("VersionNumber", "CreationDate")):
    order_col = next((c for c in order_col_candidates if c in df.columns), None)
    if order_col:
        df = df.sort_values(order_col)
    return df.drop_duplicates(group_col, keep="last")


def build_datasets_overview_and_history(files):
    if MAIN_TABLE not in files:
        sys.exit(f"{MAIN_TABLE} n'a pas pu être récupéré : impossible de continuer.")

    log(f"Chargement de {MAIN_TABLE} ...")
    main_df = pd.read_csv(files[MAIN_TABLE], low_memory=False)
    unmerged_notes = []
    versions_history = None

    for name, path in files.items():
        if name in (MAIN_TABLE, *LOOKUP_TABLES):
            continue
        base = Path(name).stem
        log(f"Traitement de {name} ...")
        try:
            df = pd.read_csv(path, low_memory=False)
        except Exception as e:
            log(f"  -> impossible de lire {name} ({e}), ignoré.")
            continue

        if FOREIGN_KEY not in df.columns:
            unmerged_notes.append(f"{name} (pas de colonne '{FOREIGN_KEY}' trouvée)")
            log(f"  -> pas de colonne '{FOREIGN_KEY}', gardé tel quel sur disque.")
            continue

        if "Version" in base:
            # Historique complet conservé à part + dernière version fusionnée dans l'overview.
            versions_history = df if versions_history is None else pd.concat(
                [versions_history, df], ignore_index=True, sort=False
            )
            latest = latest_by_group(df, FOREIGN_KEY)
            latest = latest.add_prefix(f"{base}_")
            latest = latest.rename(columns={f"{base}_{FOREIGN_KEY}": FOREIGN_KEY})
            main_df = main_df.merge(latest, left_on=MAIN_KEY, right_on=FOREIGN_KEY, how="left")
            log(f"  -> fusionné (dernière ligne par dataset, préfixe '{base}_'), "
                f"historique complet conservé dans {{out}}_versions.")

        elif base.endswith("Tags"):
            if "Tags.csv" in files:
                tags_lookup = pd.read_csv(files["Tags.csv"], low_memory=False)
                if "TagId" in df.columns and "Id" in tags_lookup.columns and "Name" in tags_lookup.columns:
                    df = df.merge(tags_lookup[["Id", "Name"]], left_on="TagId", right_on="Id", how="left")
                    agg = (
                        df.groupby(FOREIGN_KEY)["Name"]
                        .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
                        .rename("Tags")
                    )
                    main_df = main_df.merge(agg, left_on=MAIN_KEY, right_index=True, how="left")
                    log("  -> fusionné (noms de tags agrégés dans la colonne 'Tags').")
                    continue
            unmerged_notes.append(f"{name} (Tags.csv manquant ou colonnes inattendues)")

        elif base.endswith("Votes"):
            counts = df.groupby(FOREIGN_KEY).size().rename(f"{base}Count")
            main_df = main_df.merge(counts, left_on=MAIN_KEY, right_index=True, how="left")
            main_df[f"{base}Count"] = main_df[f"{base}Count"].fillna(0).astype(int)
            log(f"  -> fusionné (compte agrégé dans '{base}Count').")

        else:
            # Relation 1:1 ou 1:N inconnue -> on tente une fusion directe si 1 ligne par dataset,
            # sinon on agrège un simple compte pour ne pas perdre l'info, et on garde le fichier brut.
            if df[FOREIGN_KEY].is_unique:
                df = df.add_prefix(f"{base}_")
                df = df.rename(columns={f"{base}_{FOREIGN_KEY}": FOREIGN_KEY})
                main_df = main_df.merge(df, left_on=MAIN_KEY, right_on=FOREIGN_KEY, how="left")
                log(f"  -> fusionné directement (relation 1:1, préfixe '{base}_').")
            else:
                counts = df.groupby(FOREIGN_KEY).size().rename(f"{base}Count")
                main_df = main_df.merge(counts, left_on=MAIN_KEY, right_index=True, how="left")
                main_df[f"{base}Count"] = main_df[f"{base}Count"].fillna(0).astype(int)
                unmerged_notes.append(
                    f"{name} (relation 1:N non standard -> seul un compte '{base}Count' a été ajouté, "
                    f"fichier brut conservé sur disque pour le détail complet)"
                )
                log(f"  -> relation 1:N -> compte agrégé '{base}Count' ajouté, détail conservé sur disque.")

    # Propriétaire (Users.csv / Organizations.csv / UserOrganizations.csv)
    owner_col = next((c for c in ("OwnerUserId", "CreatorUserId") if c in main_df.columns), None)
    if "Users.csv" in files and owner_col:
        users = pd.read_csv(files["Users.csv"], low_memory=False)
        user_cols = [c for c in ("Id", "UserName", "DisplayName", "RegisterDate", "PerformanceTier")
                     if c in users.columns]
        if "Id" in user_cols and "UserName" in user_cols:
            u = users[user_cols].add_prefix("Owner_")
            main_df = main_df.merge(u, left_on=owner_col, right_on="Owner_Id", how="left")
            log(f"Propriétaire fusionné via '{owner_col}' -> {[c for c in u.columns if c != 'Owner_Id']}.")

        # Organisations auxquelles appartient le propriétaire (pas seulement l'org. propriétaire directe)
        if "UserOrganizations.csv" in files and "Organizations.csv" in files:
            uorgs = pd.read_csv(files["UserOrganizations.csv"], low_memory=False)
            orgs_lookup = pd.read_csv(files["Organizations.csv"], low_memory=False)
            org_name_col = next((c for c in ("Name", "Slug") if c in orgs_lookup.columns), None)
            if "UserId" in uorgs.columns and "OrganizationId" in uorgs.columns and org_name_col:
                uorgs = uorgs.merge(
                    orgs_lookup[["Id", org_name_col]], left_on="OrganizationId", right_on="Id", how="left"
                )
                orgs_by_user = (
                    uorgs.groupby("UserId")[org_name_col]
                    .apply(lambda names: ", ".join(sorted(set(n for n in names if pd.notna(n)))))
                    .rename("Owner_Organizations")
                )
                main_df = main_df.merge(orgs_by_user, left_on=owner_col, right_index=True, how="left")
                log("Organisations d'appartenance du propriétaire fusionnées -> Owner_Organizations "
                    "(via UserOrganizations.csv).")
            else:
                log("UserOrganizations.csv présent mais colonnes attendues introuvables, ignoré pour cet enrichissement.")

    if "Organizations.csv" in files and "OwnerOrganizationId" in main_df.columns:
        orgs = pd.read_csv(files["Organizations.csv"], low_memory=False)
        if "Id" in orgs.columns:
            name_col = next((c for c in ("Name", "Slug") if c in orgs.columns), None)
            if name_col:
                o = orgs[["Id", name_col]].add_prefix("Organization_")
                main_df = main_df.merge(
                    o, left_on="OwnerOrganizationId", right_on="Organization_Id", how="left"
                )
                log("Organisation propriétaire directe fusionnée -> Organization_" + name_col + ".")

    if unmerged_notes:
        log("\nTables non fusionnées entièrement (détail conservé tel quel sur disque) :")
        for note in unmerged_notes:
            log(f"  - {note}")

    return main_df, versions_history


def save_outputs(df, out_base, fmt, label):
    if df is None or df.empty:
        log(f"Rien à sauvegarder pour {label}.")
        return
    if fmt in ("csv", "both"):
        csv_path = Path(out_base).with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        log(f"-> CSV ({label}) : {csv_path} ({len(df)} lignes, {len(df.columns)} colonnes)")
    if fmt in ("json", "both"):
        json_path = Path(out_base).with_suffix(".json")
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        log(f"-> JSON ({label}) : {json_path} ({len(df)} entrées)")


def main():
    parser = argparse.ArgumentParser(
        description="Récupère TOUTES les métadonnées disponibles pour tous les datasets Kaggle via Meta Kaggle"
    )
    parser.add_argument("--out", default="all_datasets", help="Préfixe des fichiers de sortie")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--download-dir", default="./meta_kaggle_raw",
                         help="Dossier où stocker les CSV Meta Kaggle bruts (réutilisés si déjà présents)")
    parser.add_argument("--skip-history", action="store_true",
                         help="Ne génère que la vue d'ensemble, sans l'historique complet des versions")
    args = parser.parse_args()

    api = get_api()
    filenames, _all_names = discover_files(api)
    files = download_files(api, filenames, Path(args.download_dir))

    overview, versions_history = build_datasets_overview_and_history(files)
    log(f"\nTotal datasets : {len(overview)} lignes, {len(overview.columns)} colonnes de métadonnées.")
    save_outputs(overview, args.out, args.format, label="datasets (vue d'ensemble)")

    if not args.skip_history and versions_history is not None:
        save_outputs(versions_history, f"{args.out}_versions", args.format, label="historique des versions")


if __name__ == "__main__":
    main()