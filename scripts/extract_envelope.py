#!/usr/bin/env python3
"""Parse parsed docs to extract kernel envelopes (explicit min/max) with evidence.

Conservative rules:
- Only accept bounds when explicitly present on the same line as a support statement.
- Confidence: high when a support phrase and two bounds are on the same line; medium when two bounds
  exist without a clear support phrase; low when ambiguous/missing.
- Never widen based on inference.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PARSED_DIR = Path("docs/parsed")
MANIFEST_FILE = PARSED_DIR / "manifest.json"
OUTPUT_RULE = Path("rules/_generated/veritas_802_rhel8.yaml")

SUPPORT_PATTERNS = ["support", "certified", "compatible"]
KERNEL_REGEX = re.compile(r"4\.18\.0-[0-9]+\.el8")


def load_manifest() -> Dict[str, str]:
    if not MANIFEST_FILE.exists():
        return {}
    with MANIFEST_FILE.open() as f:
        return json.load(f)


def read_text(rel_parsed: str) -> List[str]:
    path = PARSED_DIR / rel_parsed
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def find_bounds(lines: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Return min, max, evidence_line, confidence."""
    for line in lines:
        kernels = KERNEL_REGEX.findall(line)
        if len(kernels) >= 2 and any(p in line.lower() for p in SUPPORT_PATTERNS):
            # Use first two kernels on the line, sorted
            k_sorted = sorted(set(kernels))
            return k_sorted[0], k_sorted[-1], line.strip(), "high"

    # Fallback: collect all kernels; if two+ but without support phrase
    all_k = []
    for line in lines:
        all_k.extend(KERNEL_REGEX.findall(line))
    if len(all_k) >= 2:
        k_sorted = sorted(set(all_k))
        return k_sorted[0], k_sorted[-1], "kernels found without explicit support phrase", "medium"

    return None, None, "no explicit bounds found", "low"


def build_rule(min_k: Optional[str], max_k: Optional[str], confidence: str, source_name: str) -> Dict:
    return {
        "schema_version": 1.1,
        "application": {"name": "veritas_infoscale", "version": "8.0.2"},
        "os": {"family": "rhel", "major_version": 8},
        "kernel": {
            "min": min_k,
            "max": max_k,
            "unsupported_examples": [],
        },
        "notes": {
            "risk": "Running outside the certified kernel envelope can destabilize Veritas storage and clustering modules.",
            "remediation": "Keep kernel upgrades within the certified envelope or obtain updated vendor confirmation before rollout.",
        },
        "metadata": {
            "sources": [
                {
                    "name": source_name,
                    "reference": source_name,
                    "type": "vendor_hcl",
                }
            ],
            "confidence": confidence,
            "owner": "sre-team",
            "last_reviewed": "2026-01-30",
            "review_interval_days": 90,
        },
    }


def main() -> None:
    manifest = load_manifest()
    if not manifest:
        print("No parsed artifacts to scan")
        return

    min_k = max_k = evidence = None
    confidence = "low"
    source = None

    for raw_rel, parsed_rel in manifest.items():
        lines = read_text(parsed_rel)
        if not lines:
            continue
        min_k, max_k, evidence, confidence = find_bounds(lines)
        source = raw_rel
        if confidence == "high":
            break

    OUTPUT_RULE.parent.mkdir(parents=True, exist_ok=True)

    if not min_k or not max_k:
        print("No explicit envelope extracted; marking as ambiguous")
        rule = build_rule(None, None, "low", source or "unknown")
        rule["flags"] = {"ambiguous": True}
        rule["notes"]["evidence"] = evidence
    else:
        rule = build_rule(min_k, max_k, confidence, source or "unknown")
        rule["notes"]["evidence"] = evidence
        if confidence != "high":
            rule.setdefault("flags", {})["ambiguous"] = True

    import yaml  # type: ignore

    with OUTPUT_RULE.open("w") as f:
        yaml.safe_dump(rule, f, sort_keys=False)

    print(f"Wrote generated rule to {OUTPUT_RULE}")


if __name__ == "__main__":
    main()
