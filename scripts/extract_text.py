#!/usr/bin/env python3
"""Extract raw text from vendor PDFs/HTML into data/{id}/parsed with provenance.

TXT files are copied as-is. PDF/HTML formats are stubbed with a marker until
full parsers (pdfminer, beautifulsoup) are added.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def load_pending(pending_file: Path) -> Dict[str, str]:
    if not pending_file.exists():
        return {}
    with pending_file.open() as f:
        data = json.load(f)
        return data.get("pending", {})


def save_manifest(manifest_file: Path, entries: Dict[str, str]) -> None:
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, str] = {}
    if manifest_file.exists():
        with manifest_file.open() as f:
            existing = json.load(f)
    existing.update(entries)
    with manifest_file.open("w") as f:
        json.dump(existing, f, indent=2)


def extract_file(raw_dir: Path, parsed_dir: Path, rel_path: str) -> str:
    src = raw_dir / rel_path
    out_rel = rel_path + ".txt" if not rel_path.endswith(".txt") else rel_path
    dst = parsed_dir / out_rel
    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() in {".txt"}:
        dst.write_bytes(src.read_bytes())
    elif src.suffix.lower() in {".pdf", ".html", ".htm"}:
        placeholder = (
            "EXTRACTION_PENDING: implement parser for %s; "
            "preserve provenance and re-run.\n" % src.suffix.lower()
        )
        dst.write_text(placeholder)
    else:
        dst.write_text("EXTRACTION_UNSUPPORTED: %s\n" % src.suffix.lower())

    return str(dst.relative_to(parsed_dir))


def run_for_config(config_id: str) -> None:
    raw_dir = path_resolver.raw_dir(config_id)
    parsed_dir = path_resolver.parsed_dir(config_id)
    pending_file = parsed_dir / "pending.json"
    manifest_file = parsed_dir / "manifest.json"

    pending = load_pending(pending_file)
    if not pending:
        print(f"[{config_id}] No pending artifacts to extract")
        return

    manifest_updates: Dict[str, str] = {}
    for rel in pending.keys():
        parsed_rel = extract_file(raw_dir, parsed_dir, rel)
        manifest_updates[rel] = parsed_rel
        print(f"[{config_id}] Extracted {rel} -> {parsed_rel}")

    save_manifest(manifest_file, manifest_updates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from vendor docs")
    parser.add_argument("--config-id", help="Process a single config ID (default: all)")
    args = parser.parse_args()

    if args.config_id:
        config_loader.load_config(args.config_id)
        run_for_config(args.config_id)
    else:
        for config_id in config_loader.list_config_ids():
            run_for_config(config_id)


if __name__ == "__main__":
    main()
