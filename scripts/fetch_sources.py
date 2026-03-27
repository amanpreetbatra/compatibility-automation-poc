#!/usr/bin/env python3
"""Fetch vendor documents from configured URLs into data/{id}/raw/.

For each source in configs/sources/{id}.yaml:
- If local_path is set, copies/verifies the local file.
- If url is set, downloads to data/{id}/raw/ with a .provenance.json sidecar.
- Skips sources with neither url nor local_path.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _filename_from_source(source: Dict, url: str) -> str:
    parsed = urlparse(url)
    filename = Path(parsed.path).name
    if not filename or "." not in filename:
        name = source.get("name", "doc").replace(" ", "_").replace("/", "_")
        filename = f"{name}.html"
    return filename


def write_provenance(dest: Path, source: Dict, url: str, sha256: str) -> None:
    provenance = {
        "source_name": source.get("name"),
        "source_type": source.get("type"),
        "url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
    }
    prov_path = dest.with_suffix(dest.suffix + ".provenance.json")
    prov_path.write_text(json.dumps(provenance, indent=2))


def fetch_source(config_id: str, source: Dict, raw_dir: Path) -> None:
    name = source.get("name", "unknown")
    local_path = source.get("local_path", "")
    url = source.get("url", "")

    if local_path:
        src = Path(local_path)
        if not src.exists():
            print(f"  [{name}] local_path not found: {local_path} — skipping")
            return
        dest = raw_dir / src.name
        raw_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        sha256 = sha256_file(dest)
        write_provenance(dest, source, f"file://{src.resolve()}", sha256)
        print(f"  [{name}] Copied local file -> {dest}")
        return

    if not url:
        print(f"  [{name}] No URL or local_path configured — skipping")
        return

    try:
        import requests  # type: ignore
    except ImportError:
        print(f"  [{name}] 'requests' not installed — cannot download {url}")
        return

    filename = _filename_from_source(source, url)
    dest = raw_dir / filename
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [{name}] Downloading {url} ...")
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        sha256 = sha256_file(dest)
        write_provenance(dest, source, url, sha256)
        print(f"  [{name}] Saved to {dest} (sha256={sha256[:12]}...)")
    except Exception as e:
        print(f"  [{name}] Download failed: {e}")


def run_for_config(config_id: str) -> None:
    config = config_loader.load_config(config_id)
    raw_dir = path_resolver.raw_dir(config_id)
    sources = config.get("sources", [])

    if not sources:
        print(f"[{config_id}] No sources configured")
        return

    print(f"[{config_id}] Fetching {len(sources)} source(s)...")
    for source in sources:
        fetch_source(config_id, source, raw_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch vendor documents from configured sources")
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
