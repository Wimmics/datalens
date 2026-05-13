import argparse
import json
import os
from time import perf_counter, sleep
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "input"
CHECKPOINT_EVERY = 200000
RESTART_DELAY_SECONDS = 20
RATE_LIMIT_DELAY_SECONDS = 120
# Common sort key for both datasets and models
SORT_KEY = "created_at"
# Max item limits
MAX_DATASETS = None 
MAX_MODELS = None 


def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def save_json_file(items, output_file, kind):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    # For datasets we keep a deterministic sort by created date
    if kind == "dataset":
        items = sort_dataset_entries(items)
    with output_file.open("w", encoding="utf-8") as json_file:
        json.dump(items, json_file, indent=4, default=custom_serializer, ensure_ascii=False)


def load_cursor(cursor_file):
    if not cursor_file.exists():
        return None
    raw_value = cursor_file.read_text(encoding="utf-8").strip()
    if not raw_value:
        return None
    return int(raw_value)


def save_cursor(cursor_file, cursor_value):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(f"{cursor_value}\n", encoding="utf-8")


def retry_after_seconds(response):
    if response is None:
        return None
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return max(0, int(retry_after))
    except ValueError:
        try:
            retry_after_date = parsedate_to_datetime(retry_after)
        except (TypeError, ValueError):
            return None
        if retry_after_date.tzinfo is None:
            retry_after_date = retry_after_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, int((retry_after_date - now).total_seconds()))


def dataset_id_from_entry(entry):
    if not isinstance(entry, dict):
        return None
    return entry.get("id") or entry.get("_id")


def dataset_id_from_object(dataset):
    return getattr(dataset, "id", None) or getattr(dataset, "_id", None)


def dataset_created_at_from_entry(entry):
    if not isinstance(entry, dict):
        return None

    created_at = entry.get("created_at") or entry.get("createdAt")
    if isinstance(created_at, datetime):
        return created_at
    if isinstance(created_at, str):
        try:
            return datetime.fromisoformat(created_at)
        except ValueError:
            return None
    return None


def dataset_sort_key(entry):
    created_at = dataset_created_at_from_entry(entry) or datetime.min
    dataset_id = dataset_id_from_entry(entry) or ""
    return created_at, dataset_id


def sort_dataset_entries(items):
    return sorted(items, key=dataset_sort_key, reverse=True)


def model_id_from_entry(entry):
    if not isinstance(entry, dict):
        return None
    return entry.get("id") or entry.get("_id")


def model_id_from_object(model):
    return getattr(model, "id", None) or getattr(model, "_id", None)


def load_saved_items(output_file, id_from_entry):
    if not output_file.exists():
        return [], set()

    with output_file.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError(f"Existing file must contain a list: {output_file}")

    saved_ids = set()
    for entry in data:
        entry_id = id_from_entry(entry)
        if entry_id:
            saved_ids.add(entry_id)

    return data, saved_ids


def fetch_one_run(kind, hf_api, checkpoint_every, options):
    start_time = perf_counter()

    sort_key = options.get("sort_key", SORT_KEY)
    
    if kind == "model":
        items = hf_api.list_models(sort=sort_key) if sort_key else hf_api.list_models()
        output_file = INPUT_DIR / options.get("output_file", "models.json")
        cursor_file = INPUT_DIR / options.get("cursor_file", "models.cursor")
        id_from_entry = model_id_from_entry
        id_from_object = model_id_from_object
        max_items = options.get("max_items", MAX_MODELS)
    else:
        items = hf_api.list_datasets(sort=sort_key) if sort_key else hf_api.list_datasets()
        output_file = INPUT_DIR / options.get("output_file", "datasets.json")
        cursor_file = INPUT_DIR / options.get("cursor_file", "datasets.cursor")
        id_from_entry = dataset_id_from_entry
        id_from_object = dataset_id_from_object
        max_items = options.get("max_items", MAX_DATASETS)

    items_list, saved_ids = load_saved_items(output_file, id_from_entry)
    resumed_count = len(items_list)
    newly_added = 0

    if resumed_count > 0:
        print(f"Resume mode: loaded {resumed_count} items from {output_file}")

    start_index = len(items_list)
    cursor_value = load_cursor(cursor_file)
    if cursor_value is not None and cursor_value > start_index:
        start_index = cursor_value
        print(f"Resume cursor: starting at index {start_index}")
    if start_index > 0:
        print(f"Skipping first {start_index} items to reach cursor...")

    iterator = items
    if tqdm is not None and start_index > 0:
        skip_iterator = tqdm(
            range(start_index),
            desc="Skipping items",
            unit="item",
            initial=0,
            leave=False,
        )
        for _ in skip_iterator:
            try:
                next(iterator)
            except StopIteration:
                return "completed", None

    if tqdm is not None:
        iterator = tqdm(
            iterator,
            desc=f"Fetching {kind}s",
            unit=kind,
            initial=0,
        )

    last_cursor = start_index
    try:
        for index, obj in enumerate(iterator, start=1):
            last_cursor = start_index + index

            # Check limit if specified
            if max_items is not None and len(items_list) >= max_items:
                break

            obj_id = id_from_object(obj)
            if obj_id and obj_id in saved_ids:
                continue

            items_list.append(obj.__dict__)
            if obj_id:
                saved_ids.add(obj_id)
            newly_added += 1

            if newly_added % checkpoint_every == 0:
                save_json_file(items_list, output_file, kind)
                save_cursor(cursor_file, last_cursor)
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Checkpoint saved (+{newly_added} new, total={len(items_list)}, "
                    f"elapsed={elapsed_seconds:.1f}s)."
                )
                continue
            elif tqdm is None and index % 100 == 0:
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Scanned {index} items, added {newly_added} new "
                    f"(total={len(items_list)}) in {elapsed_seconds:.1f}s"
                )
    except HfHubHTTPError as exc:
        total_elapsed_seconds = perf_counter() - start_time
        status_code = exc.response.status_code if exc.response is not None else None
        save_json_file(items_list, output_file, kind)
        save_cursor(cursor_file, last_cursor)
        if status_code == 429:
            retry_after = retry_after_seconds(exc.response)
            print(
                f"Rate limit reached after adding {newly_added} items "
                f"(total={len(items_list)}, elapsed={total_elapsed_seconds:.1f}s). "
                f"Partial data saved to {output_file}."
            )
            if retry_after is not None:
                print(f"Retry-After: {retry_after}s")
            return "rate_limited", retry_after
        raise

    total_elapsed_seconds = perf_counter() - start_time

    save_json_file(items_list, output_file, kind)
    save_cursor(cursor_file, last_cursor)

    if max_items is not None and len(items_list) >= max_items:
        print(
            f"Limit reached: +{newly_added} new {kind}s (previous={resumed_count}, total={len(items_list)}), "
            f"saved to {output_file} (elapsed={total_elapsed_seconds:.1f}s)"
        )
        return "limit_reached", None

    print(
        f"Completed fetch: +{newly_added} new {kind}s "
        f"(previous={resumed_count}, total={len(items_list)}), "
        f"saved to {output_file} (elapsed={total_elapsed_seconds:.1f}s)"
    )
    return "completed", None


def main():
    help_epilog = """Environment Variables:
  Common:
    HF_TOKEN: Hugging Face API token (optional, required only for private repos)
    HF_CHECKPOINT_EVERY: Save checkpoint every N items (default: 200000)
    HF_RESTART_DELAY_SECONDS: Delay before restart after error (default: 20)
    HF_RATE_LIMIT_DELAY_SECONDS: Delay after rate limit (default: 120)
    HF_SORT_KEY: Sort key for items (default: created_at)
    """
    
    parser = argparse.ArgumentParser(
        description="Fetch models or datasets from Hugging Face and save to JSON",
        epilog=help_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--kind", choices=["model", "dataset"], required=True, help="Type to fetch: 'model' or 'dataset'")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of items to fetch (default: no limit)")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    checkpoint_every_raw = os.getenv("HF_CHECKPOINT_EVERY", str(CHECKPOINT_EVERY))
    restart_delay_raw = os.getenv("HF_RESTART_DELAY_SECONDS", str(RESTART_DELAY_SECONDS))
    rate_limit_delay_raw = os.getenv("HF_RATE_LIMIT_DELAY_SECONDS", str(RATE_LIMIT_DELAY_SECONDS))

    try:
        checkpoint_every = int(checkpoint_every_raw)
    except ValueError as exc:
        raise ValueError("HF_CHECKPOINT_EVERY must be an integer") from exc

    try:
        restart_delay_seconds = int(restart_delay_raw)
    except ValueError as exc:
        raise ValueError("HF_RESTART_DELAY_SECONDS must be an integer") from exc

    try:
        rate_limit_delay_seconds = int(rate_limit_delay_raw)
    except ValueError as exc:
        raise ValueError("HF_RATE_LIMIT_DELAY_SECONDS must be an integer") from exc

    if checkpoint_every <= 0:
        raise ValueError("HF_CHECKPOINT_EVERY must be a positive integer")
    if restart_delay_seconds < 0:
        raise ValueError("HF_RESTART_DELAY_SECONDS must be >= 0")
    if rate_limit_delay_seconds < 0:
        raise ValueError("HF_RATE_LIMIT_DELAY_SECONDS must be >= 0")

    hf_api = HfApi(endpoint="https://huggingface.co", token=token)

    options = {}
    options["sort_key"] = os.getenv("HF_SORT_KEY", SORT_KEY)
    
    if args.kind == "model":
        options["output_file"] = "models.json"
        options["cursor_file"] = "models.cursor"
        options["max_items"] = args.max if args.max is not None else MAX_MODELS
    else:
        options["output_file"] = "datasets.json"
        options["cursor_file"] = "datasets.cursor"
        options["max_items"] = args.max if args.max is not None else MAX_DATASETS

    run_number = 1
    while True:
        print(f"Starting run #{run_number} (kind={args.kind})")
        run_status, retry_after = fetch_one_run(args.kind, hf_api, checkpoint_every, options)
        if run_status == "completed" or run_status == "limit_reached":
            return

        if run_status == "rate_limited":
            retry_delay = retry_after if retry_after is not None else rate_limit_delay_seconds
            if retry_delay > 0:
                print(f"Auto-restart in {retry_delay}s after rate limit...")
                sleep(retry_delay)

        run_number += 1


if __name__ == "__main__":
    main()
