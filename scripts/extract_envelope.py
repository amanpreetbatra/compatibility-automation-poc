#!/usr/bin/env python3
"""Parse extracted text to determine compatibility version bounds.

Conservative rules:
- Only accept bounds when explicitly present on the same line as a support statement.
- Confidence: high when a support phrase and two bounds are on the same line; medium
  when two bounds exist without a support phrase; low when ambiguous/missing.
- Never widen based on inference.

Prints HUMAN_REVIEW_NEEDED when confidence is not high (for CI to detect).
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver
from lib.version_compare import VersionComparator

SUPPORT_PATTERNS = ["support", "certified", "compatible"]


def load_manifest(manifest_file: Path) -> Dict[str, str]:
    if not manifest_file.exists():
        return {}
    with manifest_file.open() as f:
        return json.load(f)


def read_text(parsed_dir: Path, rel_parsed: str) -> List[str]:
    path = parsed_dir / rel_parsed
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def find_bounds(
    lines: List[str], comparator: VersionComparator
) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Return (min, max, evidence_line, confidence)."""
    for line in lines:
        matches = comparator.regex.findall(line)
        if len(matches) >= 2 and any(p in line.lower() for p in SUPPORT_PATTERNS):
            k_sorted = sorted(set(matches), key=comparator.sort_key)
            return k_sorted[0], k_sorted[-1], line.strip(), "high"

    # Fallback: collect all matches across all lines
    all_matches = []
    for line in lines:
        all_matches.extend(comparator.regex.findall(line))
    if len(all_matches) >= 2:
        k_sorted = sorted(set(all_matches), key=comparator.sort_key)
        return k_sorted[0], k_sorted[-1], "versions found without explicit support phrase", "medium"

    return None, None, "no explicit bounds found", "low"


def build_rule(
    config: Dict,
    min_v: Optional[str],
    max_v: Optional[str],
    confidence: str,
    evidence: Optional[str],
    source_name: str,
    ambiguous: bool,
) -> Dict:
    product = config["product"]
    platform = config["platform"]
    vc_type = config["version_constraint"]["type"]

    return {
        "schema_version": "2.0",
        "id": config["id"],
        "product": {
            "name": product["name"],
            "version": product["version"],
        },
        "platform": {
            "name": platform["name"],
            "version": platform["version"],
        },
        "compatibility": {
            "status": "supported" if min_v and max_v else "unknown",
            "version_constraint": {
                "type": vc_type,
                "min": min_v,
                "max": max_v,
                "unsupported_examples": [],
            },
        },
        "notes": {
            "risk": config.get("notes", {}).get("risk", ""),
            "remediation": config.get("notes", {}).get("remediation", ""),
            "evidence": evidence,
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
            "last_reviewed": str(date.today()),
            "review_interval_days": 90,
            "ambiguous": ambiguous,
        },
    }


def run_for_config(config_id: str) -> bool:
    """Returns True if human review is needed."""
    config = config_loader.load_config(config_id)
    comparator = VersionComparator(config["version_constraint"])
    parsed_dir = path_resolver.parsed_dir(config_id)
    manifest_file = parsed_dir / "manifest.json"
    output_rule = path_resolver.generated_rule(config_id)

    manifest = load_manifest(manifest_file)
    if not manifest:
        print(f"[{config_id}] No parsed artifacts to scan")
        ambiguous = True
        rule = build_rule(config, None, None, "low", "no parsed artifacts", "unknown", ambiguous=True)
        output_rule.parent.mkdir(parents=True, exist_ok=True)
        with output_rule.open("w") as f:
            yaml.safe_dump(rule, f, sort_keys=False)
        print(f"[{config_id}] Wrote generated rule to {output_rule}")
        print(f"HUMAN_REVIEW_NEEDED: [{config_id}] run: python scripts/human_review.py --config-id {config_id}")
        return True

    min_v = max_v = evidence = None
    confidence = "low"
    source = None

    for raw_rel, parsed_rel in manifest.items():
        lines = read_text(parsed_dir, parsed_rel)
        if not lines:
            continue
        min_v, max_v, evidence, confidence = find_bounds(lines, comparator)
        source = raw_rel
        if confidence == "high":
            break

    output_rule.parent.mkdir(parents=True, exist_ok=True)
    ambiguous = not min_v or not max_v or confidence != "high"

    rule = build_rule(config, min_v, max_v, confidence, evidence, source or "unknown", ambiguous)
    with output_rule.open("w") as f:
        yaml.safe_dump(rule, f, sort_keys=False)

    print(f"[{config_id}] Wrote generated rule to {output_rule} (confidence={confidence})")

    if ambiguous:
        print(f"HUMAN_REVIEW_NEEDED: [{config_id}] run: python scripts/human_review.py --config-id {config_id}")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract compatibility version bounds from parsed docs")
    parser.add_argument("--config-id", help="Process a single config ID (default: all)")
    args = parser.parse_args()

    needs_review = False
    if args.config_id:
        config_loader.load_config(args.config_id)
        needs_review = run_for_config(args.config_id)
    else:
        for config_id in config_loader.list_config_ids():
            if run_for_config(config_id):
                needs_review = True

    if needs_review:
        sys.exit(0)  # Not a failure; CI checks stdout for HUMAN_REVIEW_NEEDED


if __name__ == "__main__":
    main()
