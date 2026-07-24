import pandas as pd

def export_tags_to_txt(csv_file: str, txt_file: str):
    """
    Extrait les tags et leurs chemins depuis un CSV
    et les exporte dans un fichier texte.
    """

    df = pd.read_csv(csv_file)

    required_columns = {"Name", "FullPath"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    with open(txt_file, "w", encoding="utf-8") as f:
        for _, row in df[["Name", "FullPath"]].drop_duplicates().iterrows():
            f.write(f"{row['Name']}\t{row['FullPath']}\n")

export_tags_to_txt("meta_kaggle_raw/Tags.csv", "tags.txt")