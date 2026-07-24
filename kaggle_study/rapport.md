## 1. Typologie des métadonnées par entité

### 1.1 Datasets

| Catégorie fonctionnelle         | Champs Kaggle correspondants                                                      |
| -------------------------------- | --------------------------------------------------------------------------------- |
| Créateur                        | `CreatorUserId`                                                                 |
| Identifiant                      | `Owner_UserName` / `Version_Slug`                                             |
| Taille                           | `Version_TotalCompressedBytes`, `Version_TotalUncompressedBytes`              |
| Description                      | `Version_Description`                                                           |
| Licence                          | `Version_LicenseName`                                                           |
| Date de création                | `Version_CreationDate`                                                          |
| Popularité                      | `TotalDownloads`, `TotalVotes`                                                |
| **Infos manquantes**       | Dernière modification, Dataset source, Format, Article, Annotation               |
| **Infos supplémentaires** | `Version_Title`, `Version_Subtitle`, `Version_VersionNotes`, `TotalViews` |

### 1.2 Modèles

| Catégorie fonctionnelle         | Champs Kaggle correspondants                                                                                                                                      |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Créateur                        | `Owner_Organisation` / `Owner_UserName`                                                                                                                       |
| Identifiant                      | `Owner_UserName` / `CurrentVariationSlug`                                                                                                                     |
| Taille                           | `Version_TotalCompressedBytes`, `Version_TotalUncompressedBytes`                                                                                              |
| Description                      | `Version_Description`                                                                                                                                           |
| Licence                          | `LicenseName`                                                                                                                                                   |
| Date de création                | `Version_CreationDate`                                                                                                                                          |
| Popularité                      | `TotalDownloads`, `TotalVotes`                                                                                                                                |
| Bibliothèque                    | `ModelFramework`                                                                                                                                                |
| Modèle source                   | `BaseModelVariationId`                                                                                                                                          |
| **Infos manquantes**       | Dataset d'entraînement, Implémentation, Format, Article                                                                                                         |
| **Infos supplémentaires** | `Version_VariationOverview`, `Version_VariationUsage`, `Version_FineTunable`, `VariationCount`, `Version_SourceUrl`, `Version_SourceOrganizationName` |

### 1.3 Tags 

| Catégorie fonctionnelle | Tags Kaggle correspondants |
| ------------------------ | -------------------------- |
| Région                  | `geography and place`    |
| Langue                   | `language`               |
| Architecture             | `architecture`           |

---

## 2. Couverture quantitative des champs Kaggle

### 2.1 Datasets (n = 701 396)

| Champ                                                                                            | Catégorie                   | Taux de remplissage |
| ------------------------------------------------------------------------------------------------ | ---------------------------- | ------------------- |
| CreationDate                                                                                     | Date de création            | 100,0 %             |
| CreatorUserId                                                                                    | Créateur                    | 100,0 %             |
| TotalDownloads / TotalViews / TotalVotes                                                         | Popularité                  | 100,0 %             |
| OwnerUserId                                                                                      | Créateur (secondaire)       | 99,6 %              |
| Owner_DisplayName / Owner_Id / Owner_UserName                                                    | Identifiant                  | 99,5 %              |
| Version_CreationDate / Version_LicenseName / Version_Slug / Version_Title / Version_VersionNotes | Licence / date / identifiant | 99,9 %              |
| Version_TotalCompressedBytes / Version_TotalUncompressedBytes                                    | Taille                       | 99,9 %              |
| **Tags**                                                                                   | Sujet/modalité              | **35,0 %**    |
| **Version_Description**                                                                    | Description                  | **21,2 %**    |
| **Version_Subtitle**                                                                       | Info supplémentaire         | **20,1 %**    |
| OwnerOrganizationId                                                                              | Créateur (organisation)     | 0,4 %               |

### 3.2 Modèles (n = 41 671)

| Champ                                                                    | Catégorie               | Taux de remplissage |
| ------------------------------------------------------------------------ | ------------------------ | ------------------- |
| CreationDate / TotalDownloads / TotalViews / TotalVotes / VariationCount | Date / Popularité       | 100,0 %             |
| CurrentSlug                                                              | Identifiant              | 100,0 %             |
| Owner_UserName                                                           | Créateur                | 98,7 %              |
| **Tags**                                                           | Sujet/modalité          | **6,4 %**     |
| OwnerOrganizationId                                                      | Créateur (organisation) | 1,3 %               |

### Variations de modèles (n = 48 296)

| Champ                                                                                                               | Catégorie                         | Taux de remplissage |
| ------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------- |
| Id / ModelId / ModelFramework / CurrentVariationSlug                                                                | Identifiant / Bibliothèque        | 100,0 %             |
| Version_CreationDate / Version_DatasourceVersionId / Version_Id / Version_ModelVariationId / Version_ModelVersionId | Date / suivi interne               | 100,0 %             |
| LicenseName / Version_FineTunable                                                                                   | Licence / info supplémentaire     | ~99,9 %             |
| CurrentDatasourceVersionId / CurrentModelVariationVersionId                                                         | Suivi dataset source               | ~99,3 %             |
| **Version_VariationUsage**                                                                                    | Info supplémentaire (usage)       | **10,2 %**    |
| **Version_VariationOverview**                                                                                 | Info supplémentaire (description) | **10,0 %**    |
| **Version_SourceUrl**                                                                                         | Modèle source                     | **3,9 %**     |
| **Version_SourceOrganizationName**                                                                            | Modèle source                     | **3,7 %**     |
| **BaseModelVariationId**                                                                                      | Modèle source (lien direct)       | **0,8 %**     |

## 3. Comparatif avec le thésaurus DataLens (matches.json)

Le thésaurus est organisé en **7 schemes** (familles de concepts), chacun aligné avec les tags Kaggle par correspondance exacte ou floue (`fuzzy`).

| Scheme                       | Concepts du thésaurus | Concepts alignés à un tag | Taux de couverture | Dont exact   | Dont fuzzy   |
| ---------------------------- | ---------------------- | --------------------------- | ------------------ | ------------ | ------------ |
| Dataset Modality Scheme      | 9                      | 5                           | 55,6 %             | 5            | 0            |
| Machine Learning Task Scheme | 134                    | 45                          | 33,6 %             | 27           | 18           |
| Dataset Format Scheme        | 10                     | 2                           | 20,0 %             | 2            | 0            |
| Model Library Scheme         | 53                     | 6                           | 11,3 %             | 5            | 1            |
| Dataset Library Scheme       | 11                     | 1                           | 9,1 %              | 1            | 0            |
| Transformation Scheme        | 4                      | 0                           | 0,0 %              | 0            | 0            |
| Dataset Size Scheme          | 11                     | 0                           | 0,0 %              | 0            | 0            |
| **Total**              | **232**          | **59**                | **25,4 %**   | **40** | **19** |

**Top 15 des tags importants par volume de datasets couverts :**
 
| Tag Kaggle | Chemin (`full_path`) | Datasets couverts | % de l'ensemble des datasets |
|---|---|---|---|
| image | data type > image | 62 846 | 8,96 % |
| classification | task > classification | 59 280 | 8,45 % |
| tabular | data type > tabular | 16 483 | 2,35 % |
| text | data type > text | 10 733 | 1,53 % |
| computer vision | technique > computer vision | 7 033 | 1,00 % |
| image classification | task > image-classification | 2 816 | 0,40 % |
| audio | data type > audio | 2 261 | 0,32 % |
| pandas | packages > pandas | 1 863 | 0,27 % |
| multiclass classification | task > multiclass classification | 1 757 | 0,25 % |
| object detection | task > object-detection | 1 478 | 0,21 % |
| video data | data type > video data | 1 318 | 0,19 % |
| text classification | task > text-classification | 1 157 | 0,16 % |
| image segmentation | task > image-segmentation | 976 | 0,14 % |
| pytorch | packages > pytorch | 946 | 0,13 % |
| multimodal data | data type > multimodal data | 927 | 0,13 % |
 
