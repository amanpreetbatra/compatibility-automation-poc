#!/usr/bin/env python3
"""Compare generated rules to existing rules and classify safety outcome."""

import json
from pathlib import Path
from typing import Dict, Tuple

import yaml  # type: ignore

GEN_DIR = Path("rules/_generated")
BASE_DIR = Path("rules")
SUMMARY_FILE = Path("docs/parsed/diff_summary.json")


def load_rule(path: Path) -> Dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def classify(old: Dict, new: Dict) -> Tuple[str, str]:
    old_min = old.get("kernel", {}).get("min")
    old_max = old.get("kernel", {}).get("max")
    new_min = new.get("kernel", {}).get("min")
    new_max = new.get("kernel", {}).get("max")
    confidence = new.get("metadata", {}).get("confidence", "low")
    sources = new.get("metadata", {}).get("sources", [])
    ambiguous = new.get("flags", {}).get("ambiguous", False)
    has_vendor = any(s.get("type") in {"vendor_hcl", "release_notes", "advisory"} for s in sources)

    # New rule with no baseline
    if old_min is None and old_max is None:
        return "pr_block_auto_merge", "new_rule_requires_review"

    if new_min == old_min and new_max == old_max:
        return "info", "metadata_only" if old != new else "no_change"

    narrowing = (new_min is not None and old_min is not None and new_min >= old_min) and (
        new_max is not None and old_max is not None and new_max <= old_max
    )
    widening = (new_min is not None and old_min is not None and new_min < old_min) or (
        new_max is not None and old_max is not None and new_max > old_max
    )

    if widening:
        return "pr_block_auto_merge", "envelope_widened"
    if narrowing:
        return "pr_allowed_risk_reducing", "envelope_narrowed"

    return "pr_block_auto_merge", "ambiguous_change"


def main() -> None:
    if not GEN_DIR.exists():
        print("No generated rules to diff")
        return

    summary = {}

    for gen_path in GEN_DIR.glob("*.yaml"):
        base_name = gen_path.name
        base_path = BASE_DIR / base_name
        new_rule = load_rule(gen_path)
        old_rule = load_rule(base_path) if base_path.exists() else {"kernel": {"min": None, "max": None}}

        decision, reason = classify(old_rule, new_rule)

        summary[str(gen_path)] = {
            "decision": decision,
            "reason": reason,
            "old_min": old_rule.get("kernel", {}).get("min"),
            "old_max": old_rule.get("kernel", {}).get("max"),
            "new_min": new_rule.get("kernel", {}).get("min"),
            "new_max": new_rule.get("kernel", {}).get("max"),
            "confidence": new_rule.get("metadata", {}).get("confidence"),
            "ambiguous": new_rule.get("flags", {}).get("ambiguous", False),
        }

        if not new_rule.get("metadata", {}).get("sources"):
            summary[str(gen_path)]["decision"] = "pr_block_auto_merge"
            summary[str(gen_path)]["reason"] = "missing_vendor_source"
        if new_rule.get("metadata", {}).get("confidence", "low") != "high":
            summary[str(gen_path)]["decision"] = "pr_block_auto_merge"
            summary[str(gen_path)]["reason"] = "low_confidence"
        if new_rule.get("flags", {}).get("ambiguous"):
            summary[str(gen_path)]["decision"] = "pr_block_auto_merge"
            summary[str(gen_path)]["reason"] = "ambiguous"

    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_FILE.open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote diff summary to {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
