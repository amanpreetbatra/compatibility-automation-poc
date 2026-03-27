#!/usr/bin/env python3
"""Detect vendor doc changes by SHA256 hash and queue changed files for parsing.

Outputs per config:
  data/{id}/parsed/ingest_state.json  - tracked hashes of raw docs
  data/{id}/parsed/pending.json       - list of raw docs that changed since last run
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(state_file: Path) -> Dict[str, str]:
    if state_file.exists():
        with state_file.open() as f:
            data = json.load(f)
            return data.get("hashes", {})
    return {}


def save_state(state_file: Path, hashes: Dict[str, str]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w") as f:
        json.dump({"hashes": hashes}, f, indent=2)


def write_pending(pending_file: Path, changed: Dict[str, str]) -> None:
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    with pending_file.open("w") as f:
        json.dump({"pending": changed}, f, indent=2)


def run_for_config(config_id: str) -> None:
    raw = path_resolver.raw_dir(config_id)
    state_file = path_resolver.parsed_dir(config_id) / "ingest_state.json"
    pending_file = path_resolver.parsed_dir(config_id) / "pending.json"

    previous = load_state(state_file)
    current: Dict[str, str] = {}
    changed: Dict[str, str] = {}

    if not raw.exists():
        print(f"[{config_id}] No raw directory found; nothing to do")
        write_pending(pending_file, {})
        return

    for raw_path in raw.glob("**/*"):
        if raw_path.is_dir():
            continue
        rel = str(raw_path.relative_to(raw))
        digest = sha256_file(raw_path)
        current[rel] = digest
        if previous.get(rel) != digest:
            changed[rel] = digest

    save_state(state_file, current)
    write_pending(pending_file, changed)
    print(f"[{config_id}] Detected {len(changed)} changed artifacts; queued for parsing")


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect vendor doc changes")
    parser.add_argument("--config-id", help="Process a single config ID (default: all)")
    args = parser.parse_args()

    if args.config_id:
        config_loader.load_config(args.config_id)  # validate
        run_for_config(args.config_id)
    else:
        ids = config_loader.list_config_ids()
        if not ids:
            print("No configs found in configs/sources/")
            return
        for config_id in ids:
            run_for_config(config_id)


if __name__ == "__main__":
    main()
