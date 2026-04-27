import json
import os
from time import perf_counter, sleep
from datetime import datetime, timezone
from pathlib import Path
import itertools
from email.utils import parsedate_to_datetime

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "input"
OUTPUT_FILE = INPUT_DIR / "models_new.json"
CURSOR_FILE = INPUT_DIR / "models_new.cursor"
CHECKPOINT_EVERY = 200000
RESTART_DELAY_SECONDS = 0
RATE_LIMIT_DELAY_SECONDS = 120
MAX_MODELS = 10000000


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


def save_json_file(items, output_file):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
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


def model_id_from_entry(entry):
    if not isinstance(entry, dict):
        return None
    return entry.get("id") or entry.get("_id")


def model_id_from_object(model):
    return getattr(model, "id", None) or getattr(model, "_id", None)


def load_saved_models(output_file):
    if not output_file.exists():
        return [], set()

    with output_file.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError(f"Existing file must contain a list: {output_file}")

    saved_ids = set()
    for entry in data:
        entry_id = model_id_from_entry(entry)
        if entry_id:
            saved_ids.add(entry_id)

    return data, saved_ids


def fetch_one_run(hf_api, checkpoint_every):
    models = hf_api.list_models()

    start_time = perf_counter()
    models_list, saved_model_ids = load_saved_models(OUTPUT_FILE)
    resumed_count = len(models_list)
    newly_added = 0

    if resumed_count > 0:
        print(f"Resume mode: loaded {resumed_count} models from {OUTPUT_FILE}")

    start_index = len(models_list)
    cursor_value = load_cursor(CURSOR_FILE)
    if cursor_value is not None and cursor_value > start_index:
        start_index = cursor_value
        print(f"Resume cursor: starting at index {start_index}")
    if start_index > 0:
        print(f"Skipping first {start_index} models to reach cursor...")

    model_iterator = models
    if tqdm is not None and start_index > 0:
        skip_iterator = tqdm(
            range(start_index),
            desc="Skipping models",
            unit="model",
            initial=0,
            leave=False,
        )
        for _ in skip_iterator:
            try:
                next(model_iterator)
            except StopIteration:
                return "completed", None

    if tqdm is not None:
        model_iterator = tqdm(
            model_iterator,
            desc="Fetching models",
            unit="model",
            initial=0,
        )

    last_cursor = start_index
    try:
        for index, model in enumerate(model_iterator, start=1):
            last_cursor = start_index + index
            if len(models_list) >= MAX_MODELS:
                break
                
            model_id = model_id_from_object(model)
            if model_id and model_id in saved_model_ids:
                continue

            models_list.append(model.__dict__)
            if model_id:
                saved_model_ids.add(model_id)
            newly_added += 1

            if newly_added % checkpoint_every == 0:
                save_json_file(models_list, OUTPUT_FILE)
                save_cursor(CURSOR_FILE, last_cursor)
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Checkpoint saved (+{newly_added} new, total={len(models_list)}, "
                    f"elapsed={elapsed_seconds:.1f}s)."
                )
                continue
            elif tqdm is None and index % 100 == 0:
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Scanned {index} models, added {newly_added} new "
                    f"(total={len(models_list)}) in {elapsed_seconds:.1f}s"
                )
    except HfHubHTTPError as exc:
        total_elapsed_seconds = perf_counter() - start_time
        status_code = exc.response.status_code if exc.response is not None else None
        save_json_file(models_list, OUTPUT_FILE)
        save_cursor(CURSOR_FILE, last_cursor)
        if status_code == 429:
            retry_after = retry_after_seconds(exc.response)
            print(
                f"Rate limit reached after adding {newly_added} models "
                f"(total={len(models_list)}, elapsed={total_elapsed_seconds:.1f}s). "
                f"Partial data saved to {OUTPUT_FILE}."
            )
            if retry_after is not None:
                print(f"Retry-After: {retry_after}s")
            return "rate_limited", retry_after
        raise

    total_elapsed_seconds = perf_counter() - start_time

    save_json_file(models_list, OUTPUT_FILE)
    save_cursor(CURSOR_FILE, last_cursor)

    if len(models_list) >= MAX_MODELS:
        print(
            f"Limit of {MAX_MODELS} models reached: +{newly_added} new models "
            f"(previous={resumed_count}, total={len(models_list)}), "
            f"saved to {OUTPUT_FILE} (elapsed={total_elapsed_seconds:.1f}s)"
        )
        return "limit_reached", None
    
    print(
        f"Completed fetch: +{newly_added} new models "
        f"(previous={resumed_count}, total={len(models_list)}), "
        f"saved to {OUTPUT_FILE} (elapsed={total_elapsed_seconds:.1f}s)"
    )
    return "completed", None


def main():
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

    run_number = 1
    while True:
        print(f"Starting run #{run_number}")
        run_status, retry_after = fetch_one_run(hf_api, checkpoint_every)
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