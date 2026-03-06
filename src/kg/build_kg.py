import sys
import os
# Add project root to sys.path to allow running as script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import json
import sys
import time
import os
import datetime
from rdflib import Graph, Namespace, RDF, RDFS
from rdflib.namespace import DCTERMS, FOAF, XSD, DCAT
from src.parsers.huggingFace_new_parser import parse as huggingface_parse
from src.kg.kg_generator import generate_kg
import traceback

from src.logger import logging
from src.exceptions import CustomException

SPINNER = ['|', '/', '-', '\\']

MLUO = Namespace("http://example.org/mluo/ontology#")
MLUO_TH = Namespace("http://example.org/mluo/thesaurus#")
default_ns = Namespace("http://example.org/mluo/data#")

BIBO = Namespace("http://purl.org/ontology/bibo/")

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"JSON load error: {type(e).__name__}: {e}")
        raise CustomException(e, sys)


def init_graph():
    g = Graph()
    g.bind("mluo", MLUO)
    g.bind("mluo_th", MLUO_TH)
    g.bind("", default_ns) # Default namespace for data

    g.bind("dct", DCTERMS)
    g.bind("foaf", FOAF)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("dcat", DCAT)
    g.bind("bibo", BIBO)

    return g


def process_batch(data_slice, start_idx, batch_idx, total_batches):
    g = init_graph()
    errors = []
    start_time = time.time()

    for i, obj in enumerate(data_slice):
        dataset_id = obj.get("dct_identifier", obj.get("id", f"index_{start_idx + i}"))
        try:
            parsed = huggingface_parse(obj)
            # temp_g = init_graph()
            temp_g = generate_kg(parsed)
            try:
                temp_g.serialize(format="turtle")  # Test serialization
                g += temp_g  # Add to main graph only if OK
            except Exception as ser_e:
                short_msg = (
                    f"[Batch {batch_idx}] Dataset {dataset_id} idx {start_idx + i} "
                    f"SERIALIZATION ERROR: {type(ser_e).__name__}: {ser_e}"
                )
                errors.append(short_msg)
                logging.warning(short_msg)
                logging.error(traceback.format_exc())
                raise
                # continue  # skip this dataset
        except Exception as e:

            short_msg = (
                f"[Batch {batch_idx}] Dataset {dataset_id} idx {start_idx + i} "
                f"PARSE/GEN ERROR: {type(e).__name__}: {e}"
            )
           
            errors.append(short_msg)
            logging.warning(short_msg)
            logging.error(traceback.format_exc())
            raise
            # continue  # skip this dataset

        # Spinner feedback
        elapsed = time.time() - start_time
        sys.stdout.write(
            f"\rBatch {batch_idx}/{total_batches} {SPINNER[i % len(SPINNER)]} "
            f"Dataset {start_idx + i + 1}/{start_idx + len(data_slice)} | "
            f"Elapsed: {datetime.timedelta(seconds=int(elapsed))}"
        )
        sys.stdout.flush()

    return g, errors, time.time() - start_time


def save_graph(graph, filepath, batch_idx=None, errors=None):
    try:
        graph.serialize(destination=filepath, format="turtle")
        logging.info(f"Saved: {filepath}")
    except Exception as e:
        short_msg = f"[Batch {batch_idx}] Serialization error: {type(e).__name__}: {e}"
        if errors is not None:
            errors.append(short_msg)
        logging.error(short_msg)


def save_errors(errors, path="kg_errors.log"):
    if errors:
        logging.warning(f"{len(errors)} errors encountered. See: {path}")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(errors))
        except Exception as e:
            logging.error(f"Error saving errors log: {type(e).__name__}: {e}")
            raise CustomException(e, sys)


def run_batches(json_data, batch_count=10, output_dir="artifacts/kg/huggingface"):
    total = len(json_data)
    batch_size = total // batch_count + (1 if total % batch_count else 0)
    all_errors = []
    
    os.makedirs(output_dir, exist_ok=True)
    for i in range(batch_count):
        start = i * batch_size
        end = min(start + batch_size, total)
        if start >= total:
            break
        
        logging.info(f"Processing batch {i + 1}/{batch_count}: datasets {start + 1} to {end}")
        batch_data = json_data[start:end]
        graph, errors, elapsed = process_batch(batch_data, start, i + 1, batch_count)

        output_path = f"{output_dir}/output_batch_{i + 1}.ttl"
        save_graph(graph, output_path, batch_idx=i + 1, errors=errors)
        all_errors.extend(errors)

        logging.info(f"Batch {i + 1} done ({len(batch_data)} entries) in {datetime.timedelta(seconds=int(elapsed))}")

    save_errors(all_errors)

def main(choice=1):
    try:
        # JSON_PATH = "artifacts/data/huggingface_dataset.json"
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

        if choice == 0:
            JSON_PATH = os.path.join(SCRIPT_DIR, "../../case-study/data/input/huggingface_dataset.json")
            data = load_json(JSON_PATH)
            run_batches(data, batch_count=10)

        elif choice == 1:
            JSON_PATH_NEW = os.path.join(SCRIPT_DIR, "../../case-study/data/input/datasets_new.json")
            data_new = load_json(JSON_PATH_NEW)
            run_batches(data_new, batch_count=10, output_dir="artifacts/kg/huggingface_new")

        elif choice == 2:
            JSON_PATH_ = os.path.join(SCRIPT_DIR, "../../case-study/test/dataset_new_extract.json")
            data_ = load_json(JSON_PATH_)
            run_batches(data_, batch_count=1, output_dir="case-study/test")

        elif choice == 3:
            JSON_PATH_NEW_NEW = os.path.join(SCRIPT_DIR, "../../case-study/data/input/datasets_new_new.json")
            data_new_new = load_json(JSON_PATH_NEW_NEW)
            run_batches(data_new_new, batch_count=10, output_dir="artifacts/kg/huggingface_new_new")

    except Exception as e:
        logging.error(f"Fatal error: {type(e).__name__}: {e}")
        raise CustomException(e, sys)

if __name__ == "__main__":
    main(3)
