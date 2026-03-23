#!/usr/bin/env python3
"""Detect vendor doc changes by hash/version/CMDB signal and queue parsing.

Outputs:
- docs/parsed/ingest_state.json: tracked hashes of raw docs
- docs/parsed/pending.json: list of raw docs that changed since last run
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict

RAW_DIR = Path("docs/raw")
STATE_FILE = Path("docs/parsed/ingest_state.json")
PENDING_FILE = Path("docs/parsed/pending.json")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state() -> Dict[str, str]:
    if STATE_FILE.exists():
        with STATE_FILE.open() as f:
            data = json.load(f)
            return data.get("hashes", {})
    return {}


def save_state(hashes: Dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w") as f:
        json.dump({"hashes": hashes}, f, indent=2)


def write_pending(changed: Dict[str, str]) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PENDING_FILE.open("w") as f:
        json.dump({"pending": changed}, f, indent=2)


def main() -> None:
    previous = load_state()
    current = {}
    changed: Dict[str, str] = {}

    if not RAW_DIR.exists():
        print("No docs/raw directory; nothing to do")
        return

    for raw_path in RAW_DIR.glob("**/*"):
        if raw_path.is_dir():
            continue
        if raw_path.name.startswith("."):
            continue
        rel = str(raw_path.relative_to(RAW_DIR))
        digest = sha256_file(raw_path)
        current[rel] = digest
        if previous.get(rel) != digest:
            changed[rel] = digest

    save_state(current)
    write_pending(changed)
    print(f"Detected {len(changed)} changed artifacts; queued for parsing")


if __name__ == "__main__":
    main()
