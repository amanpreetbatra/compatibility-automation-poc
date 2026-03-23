#!/usr/bin/env python3
"""Download vendor source documents defined in docs/sources.yaml."""

import hashlib
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
import urllib.error
import urllib.request

import yaml  # type: ignore

CONFIG_FILE = Path("docs/sources.yaml")
RAW_DIR = Path("docs/raw")
OUTPUT_FILE = Path("docs/parsed/fetch_provenance.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config() -> List[Dict]:
    if not CONFIG_FILE.exists():
        example = (
            "docs/sources.yaml was not found.\n"
            "Example:\n"
            "sources:\n"
            "  - name: veritas_hcl_802\n"
            "    url: https://www.veritas.com/content/support/en_US/doc/infoscale_802_pcl\n"
            "    type: vendor_hcl\n"
        )
        print(example)
        return []
    with CONFIG_FILE.open() as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("sources") or []


def guess_extension(url: str, content_type: Optional[str]) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix:
        return suffix
    if content_type:
        mime = content_type.split(";", 1)[0].strip()
        if mime in {"text/html", "application/xhtml+xml"}:
            return ".html"
        if mime == "application/pdf":
            return ".pdf"
        if mime.startswith("text/plain"):
            return ".txt"
        guessed = mimetypes.guess_extension(mime)
        if guessed:
            return guessed
    return ".bin"


def sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def fetch_source(entry: Dict) -> Dict:
    name = entry.get("name", "source")
    url = entry.get("url", "")
    source_type = entry.get("type", "unknown")
    result = {
        "name": name,
        "url": url,
        "type": source_type,
        "timestamp": now_iso(),
        "status": "error",
        "path": "",
        "sha256": "",
        "size": 0,
        "content_type": "",
        "error": "",
    }

    if not url:
        result["error"] = "Missing url"
        return result

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "compatibility-automation-poc/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}: {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        result["error"] = f"Request failed: {exc.reason}"
        return result

    extension = guess_extension(url, content_type)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / f"{name}{extension}"
    output_path.write_bytes(payload)

    result.update(
        {
            "status": "ok",
            "path": str(output_path),
            "sha256": sha256_bytes(payload),
            "size": len(payload),
            "content_type": content_type,
            "error": "",
        }
    )
    return result


def main() -> None:
    sources = load_config()
    if not sources:
        return

    results = [fetch_source(entry) for entry in sources]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps({"fetched_at": now_iso(), "sources": results}, indent=2))
    print(f"Wrote fetch provenance to {OUTPUT_FILE}")
    for item in results:
        print(f"{item['name']}: {item['status']}")


if __name__ == "__main__":
    main()
