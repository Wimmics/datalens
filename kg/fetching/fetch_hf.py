import argparse
import json
from time import perf_counter, sleep, time
from datetime import datetime, UTC
from pathlib import Path
import sqlite3

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError


BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
DB_DIR = BASE_DIR / "db"
RESOURCES_DIR = BASE_DIR.parent / "processing" / "resources"
STATUS_FILE = BASE_DIR / "state" / "status.json"

DEFAULT_BATCH_SIZE = 150000
RATE_LIMIT_DELAY = 120
SORT_KEY = "created_at"


def get_storage_paths(kind):
    return {
        "db_file": DB_DIR / f"{kind}_ids.sqlite",
        "ids_json": RESOURCES_DIR / f"{kind}_ids.json",
    }


def init_db(db_file):
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-200000;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ids (
            id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    return conn


def export_ids_to_json(conn, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cursor = conn.execute("SELECT id FROM ids")

    tmp = output_path.with_suffix(".tmp")

    with tmp.open("w", encoding="utf-8") as f:
        f.write("[\n")

        first = True

        for (id_,) in cursor:
            if not first:
                f.write(",\n")
            f.write(json.dumps(id_, ensure_ascii=False))
            first = False

        f.write("\n]\n")

    tmp.replace(output_path)


def write_status(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_last_batch_index(batch_dir, kind):
    max_index = 0
    for path in batch_dir.glob(f"{kind}_batch_*.json"):
        try:
            index = int(path.stem.rsplit("_", 1)[-1])
            max_index = max(max_index, index)
        except ValueError:
            pass
    return max_index


def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def positive_int(value, name):
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0")
    return parsed


def id_from_object(item):
    return getattr(item, "id", None)


def extract_retry(response):
    if not response:
        return None
    header = response.headers.get("ratelimit")
    if not header:
        return None

    result = {}
    for part in header.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                v = int(v)
            except ValueError:
                pass
            result[k] = v

    if result.get("r", 1) == 0:
        return result.get("t")
    return None


def fetch(kind, hf_api, options):
    print(f"Starting fetch: {kind}")
    start = perf_counter()

    storage_paths = get_storage_paths(kind)
    conn = init_db(storage_paths["db_file"])

    batch_dir = INPUT_DIR / f"{kind}_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)

    buffer = []
    batch_ids = []
    known_cache = set()

    file_index = get_last_batch_index(batch_dir, kind)

    iterated = 0
    written = 0
    last_heartbeat = time()

    if kind == "models":
        items = hf_api.list_models(sort=SORT_KEY, fetch_config=True)
    else:
        items = hf_api.list_datasets(sort=SORT_KEY, fetch_config=True)

    def flush():
        nonlocal buffer, batch_ids, file_index, written

        if not buffer:
            return

        file_index += 1

        path = batch_dir / f"{kind}_batch_{file_index:02d}.json"
        tmp = path.with_suffix(".tmp")

        with tmp.open("w", encoding="utf-8") as f:
            json.dump(buffer, f, default=custom_serializer, ensure_ascii=False)

        tmp.replace(path)

        conn.execute("BEGIN")
        conn.executemany(
            "INSERT OR IGNORE INTO ids VALUES (?)",
            [(i,) for i in batch_ids]
        )
        conn.commit()

        written += len(buffer)

        buffer = []
        batch_ids = []

        write_status(STATUS_FILE, {
            "kind": kind,
            "iterated": iterated,
            "written": written,
            "timestamp": datetime.now(UTC).isoformat()
        })

        print(f"Flush batch {file_index:04d} written={written}")

    for obj in items:
        try:
            iterated += 1

            obj_id = id_from_object(obj)
            if not obj_id:
                continue

            if obj_id in known_cache:
                continue

            known_cache.add(obj_id)

            buffer.append(custom_serializer(obj))
            batch_ids.append(obj_id)

            if written >= options["max"] if options["max"] is not None else False:
                print(f"Reached max limit of {options['max']}. Stopping.")
                break

            if len(buffer) >= options["batch_size"]:
                flush()

            now = time()
            if now - last_heartbeat > 60:
                write_status(STATUS_FILE, {
                    "kind": kind,
                    "iterated": iterated,
                    "written": written,
                    "timestamp": datetime.now(UTC).isoformat()
                })
                print(f"[heartbeat] iterated={iterated} written={written} time={perf_counter() - start:.1f}s")
                last_heartbeat = now

        except HfHubHTTPError as e:
            flush()
            status = e.response.status_code if e.response else None

            if status == 429:
                wait = extract_retry(e.response) or RATE_LIMIT_DELAY
                print(f"[HTTP 429] sleep {wait}")
                sleep(wait)
                continue

            if status and 500 <= status < 600:
                print(f"[HTTP {status}] retry 30s")
                sleep(30)
                continue

            raise

        except Exception:
            flush()
            export_ids_to_json(conn, storage_paths["ids_json"])
            conn.close()
            raise

    export_ids_to_json(conn, storage_paths["ids_json"])
    conn.close()

    write_status(STATUS_FILE, {
        "kind": kind,
        "iterated": iterated,
        "written": written,
        "status": "completed",
        "timestamp": datetime.now(UTC).isoformat()
    })

    print(f"Done : written={written} iterated={iterated} time={perf_counter()-start:.1f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["models", "datasets"], required=True)
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE)

    args = parser.parse_args()

    hf_api = HfApi()

    options = {
        "batch_size": positive_int(args.batch, "batch_size"),
        "max": positive_int(args.max, "max") if args.max is not None else None,
    }

    fetch(args.kind, hf_api, options)


if __name__ == "__main__":
    main()