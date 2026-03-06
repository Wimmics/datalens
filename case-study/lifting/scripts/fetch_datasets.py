import json
import os
from time import perf_counter, sleep
from datetime import datetime
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_FILE = INPUT_DIR / "datasets_new_new.json"
CHECKPOINT_EVERY = 200000
RESTART_DELAY_SECONDS = 20
RATE_LIMIT_DELAY_SECONDS = 120


def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def save_json_file(items, output_file):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as json_file:
        json.dump(items, json_file, indent=4, default=custom_serializer)


def dataset_id_from_entry(entry):
    if not isinstance(entry, dict):
        return None
    return entry.get("id") or entry.get("_id")


def dataset_id_from_object(dataset):
    return getattr(dataset, "id", None) or getattr(dataset, "_id", None)


def load_saved_datasets(output_file):
    if not output_file.exists():
        return [], set()

    with output_file.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError(f"Existing file must contain a list: {output_file}")

    saved_ids = set()
    for entry in data:
        entry_id = dataset_id_from_entry(entry)
        if entry_id:
            saved_ids.add(entry_id)

    return data, saved_ids


def fetch_one_run(hf_api, checkpoint_every):
    datasets = hf_api.list_datasets()

    start_time = perf_counter()
    datasets_list, saved_dataset_ids = load_saved_datasets(OUTPUT_FILE)
    resumed_count = len(datasets_list)
    newly_added = 0

    if resumed_count > 0:
        print(f"Resume mode: loaded {resumed_count} datasets from {OUTPUT_FILE}")

    dataset_iterator = datasets
    if tqdm is not None:
        dataset_iterator = tqdm(
            datasets,
            desc="Fetching datasets",
            unit="dataset",
        )

    try:
        for index, dataset in enumerate(dataset_iterator, start=1):
            dataset_id = dataset_id_from_object(dataset)
            if dataset_id and dataset_id in saved_dataset_ids:
                continue

            datasets_list.append(dataset.__dict__)
            if dataset_id:
                saved_dataset_ids.add(dataset_id)
            newly_added += 1

            if newly_added % checkpoint_every == 0:
                save_json_file(datasets_list, OUTPUT_FILE)
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Checkpoint saved (+{newly_added} new, total={len(datasets_list)}, "
                    f"elapsed={elapsed_seconds:.1f}s)."
                )
                return "checkpoint"
            elif tqdm is None and index % 100 == 0:
                elapsed_seconds = perf_counter() - start_time
                print(
                    f"Scanned {index} datasets, added {newly_added} new "
                    f"(total={len(datasets_list)}) in {elapsed_seconds:.1f}s"
                )
    except HfHubHTTPError as exc:
        total_elapsed_seconds = perf_counter() - start_time
        status_code = exc.response.status_code if exc.response is not None else None
        save_json_file(datasets_list, OUTPUT_FILE)
        if status_code == 429:
            print(
                f"Rate limit reached after adding {newly_added} datasets "
                f"(total={len(datasets_list)}, elapsed={total_elapsed_seconds:.1f}s). "
                f"Partial data saved to {OUTPUT_FILE}."
            )
            return "rate_limited"
        raise

    total_elapsed_seconds = perf_counter() - start_time

    save_json_file(datasets_list, OUTPUT_FILE)

    print(
        f"Completed fetch: +{newly_added} new datasets "
        f"(previous={resumed_count}, total={len(datasets_list)}), "
        f"saved to {OUTPUT_FILE} (elapsed={total_elapsed_seconds:.1f}s)"
    )
    return "completed"


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
        run_status = fetch_one_run(hf_api, checkpoint_every)
        if run_status == "completed":
            return

        if run_status == "rate_limited":
            if rate_limit_delay_seconds > 0:
                print(f"Auto-restart in {rate_limit_delay_seconds}s after rate limit...")
                sleep(rate_limit_delay_seconds)
        else:
            if restart_delay_seconds > 0:
                print(f"Auto-restart in {restart_delay_seconds}s after checkpoint...")
                sleep(restart_delay_seconds)

        run_number += 1


if __name__ == "__main__":
    main()
