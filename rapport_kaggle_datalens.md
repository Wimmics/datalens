# Rapport sur les métadonnées Kaggle et leur couverture sémantique dans Datalens

## Objet

Ce rapport compare les métadonnées présentes dans les fichiers Kaggle et MetaKaggle du projet avec le mapping XR2RML, le thesaurus SKOS et l’ontologie OWL de Datalens. L’objectif est d’identifier ce qui est bien couvert, ce qui est seulement partiellement couvert, et ce qui reste hors du modèle sémantique actuel.

## Sources utilisées

Le rapport s’appuie sur l’ensemble des fichiers fournis en entrée, notamment :

- [README.md](README.md)
- [kg/README.md](kg/README.md)
- [ontology/README.md](ontology/README.md)
- [sparql-examples/README.md](sparql-examples/README.md)
- [expert-validation/README.md](expert-validation/README.md)
- [kg/lifting/mapping_models.ttl](kg/lifting/mapping_models.ttl)
- [ontology/datalens_o.ttl](ontology/datalens_o.ttl)
- [ontology/datalens_th.ttl](ontology/datalens_th.ttl)
- [ontology.xml](ontology.xml)
- [thesaurus.xml](thesaurus.xml)
- [ttl2xml.py](ttl2xml.py)
- [ontology.rdf](ontology.rdf)
- [kaggle_study/all_models.json](kaggle_study/all_models.json)
- [kaggle_study/all_models_variations.json](kaggle_study/all_models_variations.json)
- [kaggle_study/all_datasets.json](kaggle_study/all_datasets.json)
- [meta_kaggle_raw/Models.csv](meta_kaggle_raw/Models.csv)
- [meta_kaggle_raw/ModelVersions.csv](meta_kaggle_raw/ModelVersions.csv)
- [meta_kaggle_raw/ModelVariations.csv](meta_kaggle_raw/ModelVariations.csv)
- [meta_kaggle_raw/Datasets.csv](meta_kaggle_raw/Datasets.csv)

Les fichiers [ontology.xml](ontology.xml) et [thesaurus.xml](thesaurus.xml) sont des sérialisations RDF/XML dérivées des versions Turtle, générées par [ttl2xml.py](ttl2xml.py). Le fichier [ontology.rdf](ontology.rdf) est vide et n’apporte pas de contenu exploitable supplémentaire.

## 1. Types de métadonnées observés dans les sources Kaggle

### 1.1 `all_models.json`

Le fichier [kaggle_study/all_models.json](kaggle_study/all_models.json) contient 41 671 enregistrements et 17 colonnes dans l’échantillon observé. Il expose surtout des métadonnées de niveau ressource :

- identifiants et navigation : `Id`, `CurrentSlug`, `CurrentModelVersionId`, `ForumId`
- dates et activité : `CreationDate`
- usage et popularité : `TotalDownloads`, `TotalViews`, `TotalVotes`, `TotalKernels`, `VariationCount`, `VoteCount`
- sujet fonctionnel : `Tags`
- propriétaire : `OwnerOrganizationId`, avec des champs `OwnerUserId`, `Owner_*` souvent nuls dans l’échantillon

Le signal principal est donc une couverture forte des métadonnées structurelles et d’usage, mais une faible expressivité sémantique native : les tags restent libres et les relations métier ne sont pas encore typées.

### 1.2 `all_models_variations.json`

Le fichier [kaggle_study/all_models_variations.json](kaggle_study/all_models_variations.json) contient 48 296 enregistrements et 18 colonnes dans l’échantillon. Il documente la variante de modèle et sa version :

- identité de la variante : `Id`, `ModelId`, `CurrentVariationSlug`, `CurrentModelVariationVersionId`
- cadre technique : `ModelFramework`
- versionnement et provenance : `Version_Id`, `Version_ModelVariationId`, `Version_ModelVersionId`, `Version_DatasourceVersionId`, `Version_CreationDate`
- licence : `LicenseName`
- réutilisabilité et documentation : `Version_FineTunable`, `Version_VariationUsage`, `Version_VariationOverview`
- provenance externe : `Version_SourceOrganizationName`, `Version_SourceUrl`
- modèle de base : `BaseModelVariationId`

Cette source est la plus informative pour les aspects de famille de modèle, de framework, de dépendance à un modèle de base et de documentation d’usage. En revanche, plusieurs attributs sont lacunaires ou nuls dans l’échantillon, notamment l’organisation source, l’URL source et le modèle de base.

### 1.3 `all_datasets.json`

Le fichier [kaggle_study/all_datasets.json](kaggle_study/all_datasets.json) est le plus riche, avec 701 396 enregistrements et 34 colonnes. Il combine des métadonnées de ressource, de version et d’usage :

- identifiants et navigation : `Id`, `CurrentDatasetVersionId`, `CurrentDatasourceVersionId`, `ForumId`, `Type`, `Version_Id`, `Version_DatasetId`, `Version_Slug`, `Version_Title`
- dates : `CreationDate`, `LastActivityDate`, `Version_CreationDate`
- popularité : `TotalDownloads`, `TotalViews`, `TotalVotes`, `TotalKernels`
- ownership : `CreatorUserId`, `OwnerUserId`, `OwnerOrganizationId`, `Owner_*`
- annotation de publication : `Version_Description`, `Version_Subtitle`, `Version_VersionNotes`, `Version_LicenseName`, `Version_TotalCompressedBytes`, `Version_TotalUncompressedBytes`
- enrichissement : `Tags`, `Medal`, `MedalAwardDate`

Ce fichier couvre donc bien la dimension éditoriale des datasets, leur cycle de vie et leur popularité, avec un mélange de métadonnées techniques, sociales et descriptives.

### 1.4 Schéma brut MetaKaggle

Les CSV bruts [meta_kaggle_raw/Models.csv](meta_kaggle_raw/Models.csv), [meta_kaggle_raw/ModelVersions.csv](meta_kaggle_raw/ModelVersions.csv), [meta_kaggle_raw/ModelVariations.csv](meta_kaggle_raw/ModelVariations.csv) et [meta_kaggle_raw/Datasets.csv](meta_kaggle_raw/Datasets.csv) montrent un schéma plus réduit et plus structurel que les JSON enrichis :

- `Models.csv` : 11 colonnes, focalisées sur identifiants, version courante, activité et slug
- `ModelVersions.csv` : 9 colonnes, avec titre, sous-titre, model card, date de publication, sources de provenance
- `ModelVariations.csv` : 8 colonnes, avec slug de variation, framework, licence et lien vers la datasource
- `Datasets.csv` : 16 colonnes, avec IDs, ownership, version courante, type, activité et compteurs d’usage

La comparaison montre que les JSON de `kaggle_study/` portent déjà une couche d’enrichissement utile pour l’alignement sémantique, alors que les CSV bruts fournissent surtout la charpente relationnelle.

## 2. Couverture réelle des métadonnées observée dans les échantillons

Sur les premiers enregistrements observés, on voit une couverture élevée des champs centraux et des lacunes plus nettes sur les champs de provenance ou de documentation.

### Modèles

- couverture forte : identifiant, slug, date, métriques d’usage, tags, version courante
- couverture faible ou nulle : `OwnerUserId`, `Owner_DisplayName`, `Owner_Id`, `Owner_UserName` dans l’échantillon, ce qui suggère une prédominance d’ownership organisationnel pour certains modèles

### Variations de modèles

- couverture forte : `ModelFramework`, `CurrentVariationSlug`, identifiants de version, `Version_FineTunable`
- couverture partielle : `Version_VariationUsage`, `Version_VariationOverview`, `LicenseName`
- couverture faible ou nulle : `BaseModelVariationId`, `Version_SourceOrganizationName`, `Version_SourceUrl`

### Datasets

- couverture forte : identifiants, dates, compteurs d’usage, version courante, `Version_Title`, `Version_LicenseName`
- couverture partielle : `Tags`, `Version_Description`, `Version_Subtitle`, `Medal`
- ownership mixte : `OwnerUserId` et `OwnerOrganizationId` coexistent, ce qui rend le champ owner hétérogène mais exploitable

## 3. Comparatif avec le mapping XR2RML

Le fichier [kg/lifting/mapping_models.ttl](kg/lifting/mapping_models.ttl) montre que le pipeline cible une représentation normalisée et sémantiquement typée. Il ne copie pas les champs bruts tels quels ; il les projette vers des propriétés de l’ontologie et du thesaurus.

### 3.1 Champs bien couverts par le mapping

Le mapping modèle couvre bien les métadonnées suivantes :

- `dcterms:identifier` pour l’identifiant fonctionnel du modèle
- `dcterms:issued` pour la date de création
- `dlo:downloadCount` et `dlo:likesCount` pour les indicateurs de popularité
- `dcat:keyword` pour les tags
- `dcterms:spatial`, `dcterms:language`, `dcterms:license` pour les ressources externes normalisées
- `dlo:hasTask`, `dlo:hasModality`, `dlo:hasLibrary` pour les concepts alignés au thesaurus
- `dlo:wasTrainedOn`, `prov:wasDerivedFrom`, `prov:qualifiedDerivation` pour les relations de provenance
- `dlo:hasModelConfiguration` pour la configuration technique
- `dcat:landingPage`, `dcterms:creator`, `dcat:distribution`, `dlo:hasAcademicArticle`, `dcterms:publisher` pour les liens de ressources associées
- les accès public / restreint via des TriplesMap dédiées

Cette couverture est cohérente avec les usages des requêtes SPARQL décrites dans [sparql-examples/README.md](sparql-examples/README.md), en particulier pour les questions sur les tâches, les modalités, la provenance et la popularité.

### 3.2 Champs partiellement couverts ou absents

Le mapping modèle ne reflète pas directement plusieurs métadonnées Kaggle visibles dans les JSON et CSV :

- `OwnerOrganizationId`, `OwnerUserId`, `ForumId`, `TotalViews`, `TotalVotes`, `TotalKernels`, `VariationCount`, `VoteCount`
- `ModelFramework`, `BaseModelVariationId`, `Version_VariationUsage`, `Version_VariationOverview`
- `Version_Description`, `Version_Subtitle`, `ModelCard`, `OriginalPublishDate`, `ProvenanceSources`
- `Medal`, `MedalAwardDate`, `LastActivityDate`

Autrement dit, le mapping est déjà fort sur la couche sémantique, mais il ne capture qu’une partie de la richesse éditoriale et sociale des métadonnées Kaggle.

## 4. Comparatif avec l’ontologie OWL

L’ontologie [ontology/datalens_o.ttl](ontology/datalens_o.ttl) formalise le socle conceptuel autour de :

- `dlo:MLResource`, `dlo:Dataset`, `dlo:Model`
- `dlo:Task`, `dlo:SubTask`, `dlo:Modality`, `dlo:Library`
- `dlo:Transformation`, `dlo:Implementation`, `dlo:ModelFamily`
- `dlo:Annotation`, `dlo:SizeCategory`
- propriétés comme `dlo:downloadCount`, `dlo:likesCount`, `dlo:hasTask`, `dlo:hasSubTask`, `dlo:hasModality`, `dlo:hasLibrary`, `dlo:hasAcademicArticle`, `dlo:wasTrainedOn`, `dlo:hasModelFamily`, `dlo:hasImplementation`

Le point important est le suivant : l’ontologie sait déjà exprimer les dimensions métier les plus utiles pour les modèles ML, mais le mapping actuel n’exploite pas encore tout ce potentiel.

En particulier, la classe `dlo:ModelFamily` est présente dans [ontology/datalens_o.ttl](ontology/datalens_o.ttl#L167), tout comme la propriété `dlo:hasModelFamily` autour de la ligne correspondante, mais elle n’est pas exploitée par [kg/lifting/mapping_models.ttl](kg/lifting/mapping_models.ttl). De même, `dlo:Implementation` et `dlo:hasImplementation` existent dans l’ontologie mais restent hors du flux de mapping visible ici.

Le cas `dlo:isAvailable` est révélateur : la propriété est commentée dans l’ontologie, et le mapping comporte des TriplesMap désactivées pour `ModelAvailabilityTrue` et `ModelAvailabilityFalse`. Le besoin est donc identifié, mais il n’est pas activé dans le modèle livré.

## 5. Comparatif avec le thesaurus SKOS

Le thesaurus [ontology/datalens_th.ttl](ontology/datalens_th.ttl) fournit la couche de vocabulaire contrôlé indispensable pour réduire l’ambiguïté des tags Kaggle. Il couvre notamment :

- les modalités : `Audio`, `Image`, `Text`, `Tabular`, `TimeSeries`, `Video`, `3D`, `Geospatial`
- les transformations : `Fine-tune`, `Quantize`, `Merge`, `Adapt`
- les formats : `JSON`, `CSV`, `Parquet`, `WebDataset`, `ImageFolder`, `AudioFolder`, `Apache Arrow`, `Traces`
- les bibliothèques de datasets et de modèles
- un thésaurus de tâches et de sous-tâches hiérarchisées

Cette couverture est très adaptée aux besoins de Datalens, car elle permet de transformer des chaînes libres en concepts stables.

Le point de validation externe est également solide : [expert-validation/README.md](expert-validation/README.md) documente une évaluation humaine des associations tâche / sous-tâche sur 6 réponses, réparties sur deux questionnaires de 32 associations chacun. Cela renforce la crédibilité de la hiérarchie de tâches du thesaurus.

## 6. Lecture croisée : ce que Kaggle fournit, ce que Datalens formalise

On peut résumer l’écart entre Kaggle et Datalens ainsi :

- Kaggle fournit beaucoup de métadonnées opérationnelles et d’usage, mais avec un vocabulaire peu contraint
- Datalens fournit des classes, des propriétés et un thesaurus pour rendre ces métadonnées interrogeables et comparables
- Le mapping transforme une partie des champs Kaggle en RDF exploitable par les requêtes SPARQL et les visualisations décrites dans [README.md](README.md)

En pratique, le pipeline Datalens réussit déjà à formaliser :

- la popularité via `downloadCount` et `likesCount`
- la description sémantique via tâches, modalités, licences, langues, régions et bibliographie
- la provenance via datasets d’entraînement, modèles sources et dérivations
- l’identification technique via landing pages, créateurs, distributions et configurations

## 7. Gaps principaux et recommandations

Les principaux trous fonctionnels sont les suivants :

1. La famille de modèle n’est pas reliée explicitement à la classe `dlo:ModelFamily`, alors que le thesaurus et l’ontologie sont prêts pour cela.
2. Les notions de framework, de base model, d’overview d’usage et de model card ne sont pas reliées à des concepts OWL dédiés.
3. Les métriques sociales Kaggle comme vues, votes, kernels, médaille et activité récente restent hors du noyau sémantique.
4. L’axe “ownership” est encore simplifié, alors que les sources distinguent assez nettement utilisateur et organisation.

Recommandations prioritaires :

- ajouter un alignement explicite entre `ModelFramework` / `CurrentVariationSlug` et `dlo:ModelFamily` ou une classe spécialisée si nécessaire
- modéliser une notion d’implémentation ou de runtime pour relier les variations techniques à l’ontologie
- exposer, si utile pour les analyses, les métriques `views`, `votes`, `kernels`, `medal` et `last activity` sous des propriétés Datalens dédiées ou via une classe d’indicateurs
- conserver la stratégie actuelle de normalisation avant XR2RML, car elle permet de garder les mappings stables malgré l’hétérogénéité des sources

## 8. Conclusion

Les fichiers Kaggle et MetaKaggle montrent une couverture riche des métadonnées de ressource, de version, de popularité et de provenance. Le mapping [kg/lifting/mapping_models.ttl](kg/lifting/mapping_models.ttl) couvre déjà l’essentiel des besoins sémantiques de Datalens, surtout pour les tâches, les modalités, les bibliographies, les relations de dérivation et les compteurs d’usage.

Le thesaurus [ontology/datalens_th.ttl](ontology/datalens_th.ttl) et l’ontologie [ontology/datalens_o.ttl](ontology/datalens_o.ttl) sont suffisamment expressifs pour absorber davantage de métadonnées que ce que le mapping exploite aujourd’hui. Le vrai enjeu n’est donc pas l’absence de modèle, mais l’activation de certaines correspondances et la modélisation des champs Kaggle encore laissés de côté.

En résumé : la couverture sémantique est bonne sur le cœur analytique du projet, mais elle peut encore être étendue sur la famille de modèle, l’implémentation technique et les indicateurs sociaux Kaggle.