from rdflib import Namespace, URIRef

MLUO_TH = Namespace("http://example.org/mluo/thesaurus#")
MLUO = Namespace("http://example.org/mluo/ontology#")


def _ensure_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _extract_tag_values(tags, prefix):
    if not isinstance(tags, list):
        return []

    normalized_prefix = f"{prefix}:"
    values = []

    for tag in tags:
        if not isinstance(tag, str):
            continue
        if tag.startswith(normalized_prefix):
            values.append(tag[len(normalized_prefix):])

    return values


def _field_or_tag_values(json_obj, tags, field_name, tag_prefix):
    field_value = json_obj.get(field_name)
    if field_value is not None:
        return _ensure_list(field_value)
    return _extract_tag_values(tags, tag_prefix)


def _field_or_first_tag_value(json_obj, tags, field_name, tag_prefix):
    field_value = json_obj.get(field_name)
    if field_value is not None:
        return field_value

    values = _extract_tag_values(tags, tag_prefix)
    return values[0] if values else None

def get_modality_concept(modality_obj):
    modality_map = {
        '3d': MLUO_TH["3D"],
        'audio': MLUO_TH.Audio,
        'image': MLUO_TH.Image,
        'text': MLUO_TH.Text,
        'video': MLUO_TH.Video,
        'tabular': MLUO_TH.Tabular,
        'timeseries': MLUO_TH.TimeSeries,
    }

    if isinstance(modality_obj, str):
        return modality_map.get(modality_obj.lower(), None)
    elif isinstance(modality_obj, list):
        return [modality_map.get(mod.lower(), None) for mod in modality_obj if mod.lower() in modality_map]
    return None

def get_source_datasets(source_datasets):
    if source_datasets == "original":
        return None
    else:
        if isinstance(source_datasets, str):
            return [source_datasets.split("|")[1]] if "|" in source_datasets else []
        elif isinstance(source_datasets, list):
            return [item.split("|")[1] for item in source_datasets if isinstance(item, str) and "|" in item]
        return None



def geonames_iri_from_code(code):
    country_code_to_geonames = {
        "us": "6252001",
        "eu": "390903"
    }
    
    if not code:
        return None

    code = code.lower()
    geonames_base = "http://sws.geonames.org/"
    geoname_id = country_code_to_geonames.get(code)
    if geoname_id:
        return URIRef(f"{geonames_base}{geoname_id}/")
    else:
        return None
    
# Function to get language IRI based on code availability
def linguistic_system_iri(lang_code):
    base_639_1 = "http://id.loc.gov/vocabulary/iso639-1/"
    base_639_2 = "http://id.loc.gov/vocabulary/iso639-2/"

    def to_uri(code):
        if not code:
            return None
        elif len(code) == 2:
            return URIRef(base_639_1 + code)
        elif len(code) == 3:
            return URIRef(base_639_2 + code)
        else:
            return None
    
    if isinstance(lang_code, list):
        return [to_uri(code) for code in lang_code if to_uri(code)]

    uri = to_uri(lang_code)
    return [uri] if uri else []

license_iri_map = {
    # Creative Commons licenses (cc)
    "cc-by-4.0": "http://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-4.0": "http://creativecommons.org/licenses/by-sa/4.0/",
    "cc0-1.0": "http://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-nc-4.0": "http://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa-4.0": "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc-by-nc-nd-4.0": "http://creativecommons.org/licenses/by-nc-nd/4.0/",
    "cc-by-3.0": "http://creativecommons.org/licenses/by/3.0/",
    "cc-by-2.5": "http://creativecommons.org/licenses/by/2.5/",
    "cc-by-2.0": "http://creativecommons.org/licenses/by/2.0/",
    "cc-by-nc-sa-3.0": "http://creativecommons.org/licenses/by-nc-sa/3.0/",
    "cc-by-nc-nd-3.0": "http://creativecommons.org/licenses/by-nc-nd/3.0/",
    "cc-by-nc-3.0": "http://creativecommons.org/licenses/by-nc/3.0/",
    "cc-by-nd-4.0": "http://creativecommons.org/licenses/by-nd/4.0/",
    "cc-by-sa-3.0": "http://creativecommons.org/licenses/by-sa/3.0/",
    "cc": "http://creativecommons.org/licenses/",

    # SPDX licenses
    "mit": "https://spdx.org/licenses/MIT.html",
    "apache-2.0": "https://spdx.org/licenses/Apache-2.0.html",
    "gpl-3.0": "https://spdx.org/licenses/GPL-3.0-only.html",
    "gpl-2.0": "https://spdx.org/licenses/GPL-2.0-only.html",
    "agpl-3.0": "https://spdx.org/licenses/AGPL-3.0-only.html",
    "bsd": "https://spdx.org/licenses/BSD-2-Clause.html",
    "bsd-2-clause": "https://spdx.org/licenses/BSD-2-Clause.html",
    "bsd-3-clause": "https://spdx.org/licenses/BSD-3-Clause.html",
    "bsd-3-clause-clear": "https://spdx.org/licenses/BSD-3-Clause.html",
    "lgpl-3.0": "https://spdx.org/licenses/LGPL-3.0-only.html",
    "lgpl-2.1": "https://spdx.org/licenses/LGPL-2.1-only.html",
    "lgpl": "https://spdx.org/licenses/LGPL-2.1-only.html",
    "epl-1.0": "https://spdx.org/licenses/EPL-1.0.html",
    "epl-2.0": "https://spdx.org/licenses/EPL-2.0.html",
    "mpl-2.0": "https://spdx.org/licenses/MPL-2.0.html",
    "isc": "https://spdx.org/licenses/ISC.html",
    "osl-3.0": "https://spdx.org/licenses/OSL-3.0.html",
    "pddl": "https://spdx.org/licenses/PDDL-1.0.html",
    "zlib": "https://spdx.org/licenses/Zlib.html",
    "lppl-1.3c": "https://spdx.org/licenses/LPPL-1.3c.html",
    "postgresql": "https://spdx.org/licenses/PostgreSQL.html",
    "ofl-1.1": "https://spdx.org/licenses/OFL-1.1.html",
    "afl-3.0": "https://spdx.org/licenses/AFL-3.0.html",
    "wtfpl": "https://spdx.org/licenses/WTFPL.html",
    "artistic-2.0": "https://spdx.org/licenses/Artistic-2.0.html",
    
    # Other recognized open licenses
    "cc0-1.0": "http://creativecommons.org/publicdomain/zero/1.0/",
    "unlicense": "https://unlicense.org/",
    "gfdl": "https://www.gnu.org/licenses/fdl-1.3.html",
    "odbl": "https://opendatacommons.org/licenses/odbl/",
    "odc-by": "https://opendatacommons.org/licenses/by/",
    "cdla-permissive-2.0": "https://cdla.dev/permissive-2-0/",
    "cdla-sharing-1.0": "https://cdla.dev/sharing-1-0/",
    
    # OpenRail and related (example, may be custom, verify source)
    "openrail": "https://huggingface.co/spaces/yuntian-deng/ChatGPT-OpenAI/blob/main/LICENSES.md#openrail-license",
    "openrail++": "https://huggingface.co/spaces/yuntian-deng/ChatGPT-OpenAI/blob/main/LICENSES.md#openrail-++-license",
    "bigscience-bloom-rail-1.0": "https://bigscience.huggingface.co/bigscience/bloom-rail-1.0",
    "bigscience-openrail-m": "https://bigscience.huggingface.co/bigscience/openrail-m",
    "creativeml-openrail-m": "https://huggingface.co/datasets/bigscience/creative-ml-open-rail-m",
}
    
def get_license_objects(lic):
    if lic is None:
        return None
    
    if isinstance(lic, list):
        return [obj for item in lic for obj in [get_license_objects(item)] if obj is not None]
    else:
        lic_str = str(lic).lower()
        iri = license_iri_map.get(lic_str)
        return {
            "label": lic,
            "uri": URIRef(iri) if iri else None,
        }
    
def get_media_type(format_str):
    if format_str is None:
        return None

    format_str = str(format_str).lower()
    
    iana_base = "https://www.iana.org/assignments/media-types/"
    
    # Map your format names to (label, IANA media type path)
    media_type_map = {
        "csv": ("Comma-Separated Values", "text/csv"),
        "json": ("JSON", "application/json"),
        "parquet": ("Apache Parquet", "application/vnd.apache.parquet"),  
        "webdataset": ("WebDataset", None),   # No official IANA media type
        "text": ("Plain Text", "text/plain"),
        "audiofolder": ("Audio Folder", None), # No official IANA media type
        "imagefolder": ("Image Folder", None), # No official IANA media type
        "arrow": ("Apache Arrow", None) # No official IANA media type (two options on IANA : arrow file or stream)
    } 
    
    if format_str not in media_type_map:
        return {
            "label": format_str.capitalize(),
            "uri": None
        }
    
    label, media_type = media_type_map[format_str]
    uri = f"{iana_base}{media_type}" if media_type else None

    return {
        "label": label,
        "uri": uri
    }


def parse(json_obj):
    """
    Transforms a Hugging Face JSON object into a structured dictionary
    for RDF instantiation via the MLUO vocabulary.

    :param json_obj: dict JSON representing a HF dataset
    :return: structured dict for RDF
    """
    tags = json_obj.get("tags")

    region = _field_or_first_tag_value(json_obj, tags, "region", "region")
    languages = _field_or_tag_values(json_obj, tags, "language", "language")
    licenses = _field_or_tag_values(json_obj, tags, "license", "license")
    formats = _field_or_tag_values(json_obj, tags, "format", "format")
    modalities = _field_or_tag_values(json_obj, tags, "modality", "modality")
    size_categories = _field_or_tag_values(json_obj, tags, "size_categories", "size_categories")
    source_datasets = _field_or_tag_values(json_obj, tags, "source_datasets", "source_datasets")

    task_ids = _field_or_tag_values(json_obj, tags, "task_ids", "task_ids")
    task_categories = _field_or_tag_values(json_obj, tags, "task_categories", "task_categories")
    language_creators = _field_or_tag_values(json_obj, tags, "language_creators", "language_creators")
    annotation_creators = _field_or_tag_values(json_obj, tags, "annotations_creators", "annotations_creators")

    dois = _field_or_tag_values(json_obj, tags, "doi", "doi")
    arxivs = _field_or_tag_values(json_obj, tags, "arxiv", "arxiv")

    dct_format = get_media_type(formats[0]) if formats else get_media_type(json_obj.get("format"))
    dct_license = get_license_objects(licenses) if licenses else get_license_objects(json_obj.get("license"))

    parsed = {
        
        # custom terms
        "likesCount": json_obj.get("likes"),
        "downloadCount": json_obj.get("downloads"),
        "isAvailable": False if json_obj.get("disabled") else True,

        # DCAT / DCTERMS terms
        "dct_identifier": json_obj.get("id"),
        "dct_spatial": geonames_iri_from_code(region),
        "dct_language": linguistic_system_iri(languages),
        "dct_created": json_obj.get("created_at"),
        "dct_modified": json_obj.get("last_modified"),
        "dct_description": json_obj.get("description"),
        "dct_license": dct_license,
        "dct_format": dct_format,
        "dct_accessRights": "private" if json_obj.get("private") else "public",
        "dct_source": get_source_datasets(source_datasets),
        "dct_size": size_categories,
        "dct_contributor": json_obj.get("author"),
        "dct_publisher": "HuggingFace",
        "dcat_landingPage": f"https://huggingface.co/datasets/{json_obj.get('id')}",
        "hasModality": get_modality_concept(modalities),
        "dct_subject": json_obj.get("tags", None),

        # Scientific Articles
        "hasAcademicArticle": {
            "doi": dois,
            "arxiv":  arxivs,
            "paperswithcode_id": json_obj.get("paperswithcode_id")
        },
    
        # Annotations
        "hasAnnotation": {
            "linguisticMethod": language_creators,
            "annotationMethod": annotation_creators,
            "dct_title": json_obj.get("annotation")
        },

        # Usage
        "hasUsage": {
            "hasTask": task_ids,
            "hasTaskCategory": task_categories
        }
    }

    return parsed