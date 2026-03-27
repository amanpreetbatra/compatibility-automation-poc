#!/usr/bin/env python3
"""Compare generated rules to baseline rules and classify safety outcome."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver
from lib.version_compare import VersionComparator


def load_rule(path: Path) -> Dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _get_bounds(rule: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Extract min/max from rule, supporting both schema v1.1 and v2.0."""
    # v2.0 schema
    vc = rule.get("compatibility", {}).get("version_constraint", {})
    if vc:
        return vc.get("min"), vc.get("max")
    # v1.1 schema (legacy)
    kernel = rule.get("kernel", {})
    return kernel.get("min"), kernel.get("max")


def classify(old: Dict, new: Dict, comparator: VersionComparator) -> Tuple[str, str]:
    old_min, old_max = _get_bounds(old)
    new_min, new_max = _get_bounds(new)
    confidence = new.get("metadata", {}).get("confidence", "low")
    sources = new.get("metadata", {}).get("sources", [])
    ambiguous = new.get("metadata", {}).get("ambiguous", new.get("flags", {}).get("ambiguous", False))
    has_vendor = any(
        s.get("type") in {"vendor_hcl", "release_notes", "advisory"} for s in sources
    )

    if old_min is None and old_max is None:
        return "pr_block_auto_merge", "new_rule_requires_review"

    if new_min == old_min and new_max == old_max:
        return "info", "metadata_only" if old != new else "no_change"

    try:
        narrowing = (
            new_min is not None
            and old_min is not None
            and comparator.compare(new_min, old_min) >= 0
        ) and (
            new_max is not None
            and old_max is not None
            and comparator.compare(new_max, old_max) <= 0
        )
        widening = (
            new_min is not None
            and old_min is not None
            and comparator.compare(new_min, old_min) < 0
        ) or (
            new_max is not None
            and old_max is not None
            and comparator.compare(new_max, old_max) > 0
        )
    except ValueError:
        return "pr_block_auto_merge", "version_parse_error"

    if widening:
        return "pr_block_auto_merge", "envelope_widened"
    if narrowing:
        return "pr_allowed_risk_reducing", "envelope_narrowed"
    return "pr_block_auto_merge", "ambiguous_change"


def run_for_config(config_id: str) -> Dict:
    config = config_loader.load_config(config_id)
    comparator = VersionComparator(config["version_constraint"])
    gen_rule_path = path_resolver.generated_rule(config_id)
    base_rule_path = path_resolver.baseline_rule(config_id)
    summary_file = path_resolver.diff_summary(config_id)

    if not gen_rule_path.exists():
        print(f"[{config_id}] No generated rule found; skipping diff")
        return {}

    new_rule = load_rule(gen_rule_path)
    old_rule = (
        load_rule(base_rule_path)
        if base_rule_path.exists()
        else {"compatibility": {"version_constraint": {"min": None, "max": None}}}
    )

    decision, reason = classify(old_rule, new_rule, comparator)
    old_min, old_max = _get_bounds(old_rule)
    new_min, new_max = _get_bounds(new_rule)

    entry: Dict = {
        "decision": decision,
        "reason": reason,
        "old_min": old_min,
        "old_max": old_max,
        "new_min": new_min,
        "new_max": new_max,
        "confidence": new_rule.get("metadata", {}).get("confidence"),
        "ambiguous": new_rule.get("metadata", {}).get("ambiguous", False),
    }

    # Override decision for blocking conditions
    if not new_rule.get("metadata", {}).get("sources"):
        entry["decision"] = "pr_block_auto_merge"
        entry["reason"] = "missing_vendor_source"
    if new_rule.get("metadata", {}).get("confidence", "low") != "high":
        entry["decision"] = "pr_block_auto_merge"
        entry["reason"] = "low_confidence"
    if new_rule.get("metadata", {}).get("ambiguous", False):
        entry["decision"] = "pr_block_auto_merge"
        entry["reason"] = "ambiguous"

    summary = {config_id: entry}
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"[{config_id}] diff={reason} decision={decision}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff generated rules against baselines")
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
