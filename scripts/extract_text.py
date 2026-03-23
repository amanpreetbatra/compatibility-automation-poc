#!/usr/bin/env python3
"""Extract raw text from vendor PDFs/HTML into docs/parsed with provenance.

This is a deterministic placeholder: TXT files are copied; other formats are
stubbed with a marker until full parsers (e.g., pdfminer/beautifulsoup) are added.
"""

import json
from pathlib import Path
from typing import Dict

RAW_DIR = Path("docs/raw")
PARSED_DIR = Path("docs/parsed")
PENDING_FILE = PARSED_DIR / "pending.json"
MANIFEST_FILE = PARSED_DIR / "manifest.json"


def load_pending() -> Dict[str, str]:
    if not PENDING_FILE.exists():
        return {}
    with PENDING_FILE.open() as f:
        data = json.load(f)
        return data.get("pending", {})


def save_manifest(entries: Dict[str, str]) -> None:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if MANIFEST_FILE.exists():
        with MANIFEST_FILE.open() as f:
            existing = json.load(f)
    existing = {
        raw_rel: parsed_rel
        for raw_rel, parsed_rel in existing.items()
        if not Path(raw_rel).name.startswith(".")
    }
    existing.update(entries)
    with MANIFEST_FILE.open("w") as f:
        json.dump(existing, f, indent=2)


def extract_file(rel_path: str) -> str:
    src = RAW_DIR / rel_path
    if src.name.startswith("."):
        return ""
    out_rel = rel_path + ".txt" if not rel_path.endswith(".txt") else rel_path
    dst = PARSED_DIR / out_rel
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

    return str(dst.relative_to(PARSED_DIR))


def main() -> None:
    pending = load_pending()
    if not pending:
        print("No pending artifacts to extract")
        return

    manifest_updates: Dict[str, str] = {}
    for rel in pending.keys():
        parsed_rel = extract_file(rel)
        if not parsed_rel:
            continue
        manifest_updates[rel] = parsed_rel
        print(f"Extracted {rel} -> {parsed_rel}")

    save_manifest(manifest_updates)


if __name__ == "__main__":
    main()
