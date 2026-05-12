from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def split_json_into_batches(input_file: Path, output_dir: Path, batch_count: int, prefix: str) -> list[Path]:
    """Split a JSON array file into `batch_count` files.

    The split keeps original order and distributes records as evenly as possible.
    """
    if batch_count <= 0:
        raise ValueError("batch_count must be > 0")

    with input_file.open("r", encoding="utf-8") as f:
        data: Any = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {input_file}")

    total = len(data)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_size, remainder = divmod(total, batch_count)
    written_files: list[Path] = []
    start = 0

    for index in range(batch_count):
        size = base_size + (1 if index < remainder else 0)
        end = start + size
        chunk = data[start:end]

        out_file = output_dir / f"{prefix}_batch_{index + 1:02d}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)

        written_files.append(out_file)
        start = end

    return written_files


def run_default_splits(input_root: Path, dataset_batch_count: int, model_batch_count: int) -> None:
    datasets_file = input_root / "datasets.json"
    models_file = input_root / "models.json"

    datasets_out = input_root / "datasets_batches"
    models_out = input_root / "models_batches"

    dataset_files = split_json_into_batches(
        input_file=datasets_file,
        output_dir=datasets_out,
        batch_count=dataset_batch_count,
        prefix="datasets",
    )
    model_files = split_json_into_batches(
        input_file=models_file,
        output_dir=models_out,
        batch_count=model_batch_count,
        prefix="models",
    )

    print(f"datasets: {len(dataset_files)} batches written to {datasets_out}")
    print(f"models: {len(model_files)} batches written to {models_out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split input/datasets.json into 8 batches and input/models.json into 24 batches."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "input",
        help="Path to the input folder (default: lifting/input)",
    )
    parser.add_argument(
        "--dataset-batch-count",
        type=int,
        default=8,
        help="Number of batches to split datasets into (default: 8)",
    )
    parser.add_argument(
        "--model-batch-count",
        type=int,
        default=24,
        help="Number of batches to split models into (default: 24)",
    )

    args = parser.parse_args()

    run_default_splits(args.input_root, args.dataset_batch_count, args.model_batch_count)


if __name__ == "__main__":
    main()
