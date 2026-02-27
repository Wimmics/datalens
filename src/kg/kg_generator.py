from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import DCTERMS, RDF, DCAT, XSD, FOAF, PROV, RDFS
import hashlib
from pathlib import Path

BIBO = Namespace("http://purl.org/ontology/bibo/")
MLUO = Namespace("http://example.org/mluo/ontology#")
MLUO_TH = Namespace("http://example.org/mluo/thesaurus#")
default_ns = Namespace("http://example.org/mluo/data#")


def _normalize_concept_id(value):
    if value is None:
        return ""
    return str(value).strip().replace("_", "-").lower()


def _load_thesaurus_task_map():
    thesaurus_path = Path(__file__).resolve().parents[2] / "ontology" / "mluo_thesaurus.ttl"
    task_map = {}

    try:
        thesaurus_graph = Graph()
        thesaurus_graph.parse(thesaurus_path, format="turtle")

        for task_uri in thesaurus_graph.subjects(RDF.type, MLUO.Task):
            if not isinstance(task_uri, URIRef):
                continue
            task_uri_str = str(task_uri)
            if not task_uri_str.startswith(str(MLUO_TH)):
                continue

            local_name = task_uri_str.split("#", 1)[-1]
            task_map[_normalize_concept_id(local_name)] = local_name
    except Exception:
        return {}

    return task_map


THESAURUS_TASK_MAP = _load_thesaurus_task_map()

# Create usage URI based on tasks and categories
def safe_join(items):
    if isinstance(items, list):
        # filter out None and empty strings, convert each to string
        filtered = [str(i) for i in items if i is not None and i != '']
        return '_'.join(filtered)
    else:
        return str(items) if items is not None else ''
    
def hash_id(str):
    if not str:
        return ""
    # Create SHA-256 hash of the string encoded as utf-8
    hash_obj = hashlib.sha256(str.encode('utf-8'))
    # Return first 8 characters of the hex digest (you can choose length)
    return hash_obj.hexdigest()[:8]
    
def add_license(g, distribution_uri, license_obj):
    license_name = license_obj.get("label", "Unknown License")
    license_url = license_obj.get("uri", None)

    license_uri = URIRef(f"{default_ns}license/{license_name.replace(' ', '_')}")

    # Declare the instance as a dcterms:LicenseDocument
    g.add((license_uri, RDF.type, DCTERMS.LicenseDocument))

    # Add rdfs:label
    g.add((license_uri, RDFS.label, Literal(license_name)))

    if license_url is not None:
        # Add link to SPDX license URI
        g.add((license_uri, RDFS.seeAlso, URIRef(license_url)))

    g.add((distribution_uri, DCTERMS.license, license_uri))

def add_media_type(g, distribution_uri, media_obj):
    media_label = media_obj.get("label", "Unknown Format")
    media_url = media_obj.get("uri", None)

    # Create URI for the media type instance
    media_uri = URIRef(f"{default_ns}format/{media_label.replace(' ', '_')}")

    # Declare the instance as a dcterms:MediaTypeOrExtent
    g.add((media_uri, RDF.type, DCTERMS.MediaTypeOrExtent))

    # Add rdfs:label
    g.add((media_uri, RDFS.label, Literal(media_label)))

    # Optionally add seeAlso link to IANA
    if media_url is not None:
        g.add((media_uri, RDFS.seeAlso, URIRef(media_url)))

    # Link the format to the distribution
    g.add((distribution_uri, DCTERMS.format, media_uri))

def add_task(g, usage_uri, task_id):
    normalized_task_id = _normalize_concept_id(task_id)
    thesaurus_task_local_name = THESAURUS_TASK_MAP.get(normalized_task_id)

    if thesaurus_task_local_name:
        task_uri = URIRef(f"{MLUO_TH}{thesaurus_task_local_name}")
    else:
        task_uri = URIRef(f"{default_ns}task/{task_id.replace(' ', '_')}")
        g.add((task_uri, RDF.type, MLUO.Task))
        g.add((task_uri, RDFS.label, Literal(task_id)))

    g.add((usage_uri, MLUO.hasTask, task_uri))

def add_task_category(g, usage_uri, category_id):
    normalized_category_id = _normalize_concept_id(category_id)
    thesaurus_category_local_name = THESAURUS_TASK_MAP.get(normalized_category_id)

    if thesaurus_category_local_name:
        category_uri = URIRef(f"{MLUO_TH}{thesaurus_category_local_name}")
    else:
        category_uri = URIRef(f"{default_ns}task_category/{category_id.replace(' ', '_')}")
        g.add((category_uri, RDF.type, MLUO.TaskCategory))
        g.add((category_uri, RDFS.label, Literal(category_id)))
    g.add((usage_uri, MLUO.hasTaskCategory, category_uri))

def generate_kg(data):

    g = Graph()
    
    # create a base URI for the dataset
    # This is typically the identifier of the dataset based on the id in the parsed data
    dataset_name = data.get("dct_identifier", None)
    if dataset_name == None:
        return g
    
    dataset_id = hash_id(dataset_name)
    dataset_uri = URIRef(f"{default_ns}dataset/{dataset_id}")

    g.add((dataset_uri, RDF.type, DCAT.Dataset))
    g.add((dataset_uri, DCTERMS.identifier, Literal(dataset_name)))


    landing_page = data.get("dcat_landingPage", None)
    if landing_page is not None:
        g.add((dataset_uri, DCAT.landingPage, URIRef(landing_page)))

    spatial_uri = data.get("dct_spatial", None)
    if spatial_uri is not None:
        g.add((dataset_uri, DCTERMS.spatial, spatial_uri)) # Spatial should be a geonames IRI

    created = data.get("dct_created", None)
    if created is not None:
        g.add((dataset_uri, DCTERMS.issued, Literal(created, datatype=XSD.dateTime)))

    modified = data.get("dct_modified", None) 
    if modified is not None:
        g.add((dataset_uri, DCTERMS.modified, Literal(modified, datatype=XSD.dateTime)))

    description = data.get("dct_description")
    if description is not None:
        g.add((dataset_uri, DCTERMS.description, Literal(description)))

    access_rights = data.get("dct_accessRights")
    if access_rights is not None:
        g.add((dataset_uri, DCTERMS.accessRights, Literal(access_rights)))

    creator = data.get("dct_contributor")
    if creator is not None:
        creator_uri = URIRef(f"{default_ns}creator/{creator}")
        g.add((creator_uri, RDF.type, FOAF.Agent))
        g.add((creator_uri, FOAF.name, Literal(creator)))
        g.add((dataset_uri, DCTERMS.creator, creator_uri))

    languages = data.get("dct_language", [])
    for lang in languages:
        if lang is not None:
            g.add((dataset_uri, DCTERMS.language, lang)) # Language should be a IRI from ISO 639-1 or ISO 639-2

    source_datasets = data.get("dct_source")
    if source_datasets != None:
        if isinstance(source_datasets, list):
            for source in source_datasets:
                source_id = hash_id(source)
                g.add((dataset_uri, PROV.wasDerivedFrom, URIRef(f"{default_ns}dataset/{source_id}")))

    publisher = data.get("dct_publisher", None)
    if publisher != None:
        publisher_uri = URIRef(f"{default_ns}publisher/{publisher}")
        g.add((publisher_uri, RDF.type, FOAF.Organization))
        g.add((publisher_uri, FOAF.name, Literal(publisher)))
        g.add((dataset_uri, DCTERMS.publisher, publisher_uri))

    distribution_uri = URIRef(f"{default_ns}distribution/{dataset_id}")
    g.add((distribution_uri, RDF.type, DCAT.Distribution))
    g.add((distribution_uri, DCAT.accessURL, URIRef(landing_page) if landing_page else dataset_uri))
    g.add((dataset_uri, DCAT.distribution, distribution_uri))

    format = data.get("dct_format", None)
    if format is not None:
        add_media_type(g, distribution_uri, format)

    licenses = data.get("dct_license")
    if licenses is not None:
        if isinstance(licenses, list):
            for lic in licenses:
               add_license(g, distribution_uri, lic)
        else:
            add_license(g, distribution_uri, licenses)

    

    size = data.get("dct_size")
    if size is not None:
        g.add((dataset_uri, MLUO.rowsSize, Literal(data.get("dct_size"))))

    g.add((dataset_uri, MLUO.availabilityStatus, Literal(data.get("isAvailable"), datatype=XSD.boolean)))
    g.add((dataset_uri, MLUO.likesCount, Literal(data.get("likesCount"))))
    g.add((dataset_uri, MLUO.downloadCount, Literal(data.get("downloadCount"))))    

    subject = data.get("dct_subject", None)
    if subject is not None:
        if isinstance(subject, list):
            for sub in subject:
                g.add((dataset_uri, DCTERMS.subject, Literal(sub)))
        else:
            g.add((dataset_uri, DCTERMS.subject, Literal(subject)))

    # Modality
    modality = data.get("hasModality")
    if modality is not None:
        values = [modality] if isinstance(modality, str) else modality
        for mod in values:
            if mod:
                g.add((dataset_uri, MLUO.hasModality, mod))
        
            
    # Add Annotation information if available
    # Annotations are optional, so we check if they exist in the data
    annotations = data.get("hasAnnotation", {})
    if annotations and any(annotations.values()) :
        if not annotations.get("dct_title"):
            annotations["dct_title"] = "default_annotation"

        ling_method = annotations.get('linguisticMethod', None)
        ling_method = [ling_method] if isinstance(ling_method, str) else ling_method

        ann_method = annotations.get('annotationMethod', None)
        ann_method = [ann_method] if isinstance(ann_method, str) else ann_method

        ling_str = safe_join(ling_method)
        ann_str = safe_join(ann_method)
        annotation_id = hash_id(f"{ling_str}_{ann_str}")
        annotation_uri = URIRef(f"{default_ns}annotation/{annotation_id}")
        
        g.add((annotation_uri, RDF.type, MLUO.Annotation))

        if ling_method is not None:
            for ling in ling_method:
                if ling:
                    g.add((annotation_uri, MLUO.linguisticMethod, Literal(ling)))
        
        if ann_method is not None:
            for ann in ann_method:
                if ann:
                    g.add((annotation_uri, MLUO.annotationMethod, Literal(ann)))

        g.add((dataset_uri, MLUO.hasAnnotation, annotation_uri))


    # Add Usage information if available
    # Usage is optional, so we check if it exists in the data
    # Usage can include tasks and task categories
    # If usage is not present, we skip this part
    usage = data.get("hasUsage", {})
    if usage and any(usage.values()):

        task_ids = usage.get("hasTask", [])
        task_categories = usage.get("hasTaskCategory", [])

        task_str = safe_join(task_ids)
        category_str = safe_join(task_categories)

        # Avoid trailing underscore if either is empty
        if task_str and category_str:
            usage_id = hash_id(f"{task_str}_{category_str}")
        elif task_str:
            usage_id = hash_id(task_str)
        elif category_str:
            usage_id = hash_id(category_str)
        else:
            # fallback if both empty
            usage_id = "unknown"
            
        usage_uri = URIRef(f"{default_ns}usage/{usage_id}")
        g.add((usage_uri, RDF.type, MLUO.Usage))
        g.add((dataset_uri, MLUO.hasUsage, usage_uri))

        # Task
        if isinstance(task_ids, str):
            add_task(g, usage_uri, task_ids)
        elif isinstance(task_ids, list):
            for task_id in task_ids:
                if task_id:
                    add_task(g, usage_uri, task_id)

        # TaskCategory
        if isinstance(task_categories, str):
            add_task_category(g, usage_uri, task_categories)
        elif isinstance(task_categories, list):
            for cat in task_categories:
                if cat:
                    add_task_category(g, usage_uri, cat)


    # Add Scientific Article information if available
    # Scientific articles are optional, so we check if they exist in the data
    article_info =  data.get("hasAcademicArticle", {})
    if article_info and any(article_info.values()):
        
        doi = article_info.get("doi", None)
        doi = [doi] if isinstance(doi, str) else doi

        arxiv = article_info.get("arxiv", None)
        arxiv = [arxiv] if isinstance(arxiv, str) else arxiv
        
        paperswithcode_id = article_info.get("paperswithcode_id", None)
        paperswithcode_id = [paperswithcode_id] if isinstance(paperswithcode_id, str) else paperswithcode_id

        # Determine the article URI based on priority: doi > arxiv > paperswithcode_id
        article_id = 'default'
        if doi:
            article_id = hash_id(f"doi_{'_'.join(doi)}")
        elif arxiv:
            article_id = hash_id(f"arxiv_{'_'.join(arxiv)}")
        elif paperswithcode_id:
            article_id = hash_id(f"pwc_{'_'.join(paperswithcode_id)}")
        
        article_uri = URIRef(f"{default_ns}article/{article_id}")
        g.add((article_uri, RDF.type, MLUO.AcademicArticle))
        g.add((dataset_uri, MLUO.hasAcademicArticle, article_uri))

        # Add identifiers to the article URI    
        if doi:
            for value in doi:
                g.add((article_uri, BIBO.doi, Literal(value)))
        
        if arxiv:
            for value in arxiv:
                g.add((article_uri, MLUO.arxiv, Literal(value)))

        if paperswithcode_id:
            for value in paperswithcode_id:
                g.add((article_uri, MLUO.paperswithcode_id, Literal(value)))
            
    
    return g

