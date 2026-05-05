#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


def fix_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    landing_re = re.compile(
        r"dcat:landingPage\s+<https://huggingface\.co/(?:datasets/)?([^>]+)>\s*[\.;]\s*$"
    )
    ident_re = re.compile(r"\s*dcterms:identifier\s+\"([^\"]*)\"\s*[\.;]\s*$")

    changed = 0
    for i, line in enumerate(lines):
        m = landing_re.search(line)
        if not m:
            continue

        id = m.group(1)
        for j in range(max(0, i - 8), i):
            m2 = ident_re.match(lines[j])
            if not m2:
                continue

            current = m2.group(1)
            if current != id:
                print(f"{path}: replacing line {j + 1}: '{current}' -> '{id}'")
                lines[j] = lines[j].replace(current, id)
                changed += 1
            break

    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{path}: updated {changed} identifier(s)")
    else:
        print(f"{path}: no changes")

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix dcterms:identifier so it matches the id in dcat:landingPage (preserves '__')."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "TTL files to process. If omitted, defaults to xr2rml_output/datasets/datasets_extract.ttl"
        ),
    )
    args = parser.parse_args()

    files = args.files or ["xr2rml_output/datasets/datasets_extract.ttl"]
    total_changed = 0
    for f in files:
        path = Path(f)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        total_changed += fix_file(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
