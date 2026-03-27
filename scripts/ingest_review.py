#!/usr/bin/env python3
"""Ingest a completed human review response into the baseline rule.

The response YAML is produced by filling in:
  human_reviews/{config-id}/YYYY-MM-DD_response_template.yaml

After ingestion, the baseline rule is updated and diff + test generation are re-run.

Usage:
  python scripts/ingest_review.py --config-id veritas-infoscale_rhel \\
      --review human_reviews/veritas-infoscale_rhel/2026-03-26_response_template.yaml
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def load_yaml(path: Path) -> Dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Merge override into base. None values in override keep base value."""
    result = dict(base)
    for key, val in override.items():
        if val is None:
            continue  # keep existing
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], val)
        elif isinstance(val, list) and val:
            result[key] = val  # non-empty list overwrites
        elif val != "" and val is not None:
            result[key] = val
    return result


def validate_response(response: Dict, config_id: str) -> None:
    vc = response.get("compatibility", {}).get("version_constraint", {})
    if not vc.get("min") or not vc.get("max"):
        raise ValueError(
            f"Response must include compatibility.version_constraint.min and .max.\n"
            f"Please fill in the response template and try again."
        )
    confidence = response.get("metadata", {}).get("confidence", "")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(
            f"metadata.confidence must be 'high', 'medium', or 'low'. Got: '{confidence}'"
        )


def ingest(config_id: str, review_path: Path) -> None:
    config = config_loader.load_config(config_id)
    baseline_path = path_resolver.baseline_rule(config_id)

    if not review_path.exists():
        print(f"Error: Response file not found: {review_path}")
        sys.exit(1)

    response = load_yaml(review_path)
    validate_response(response, config_id)

    # Load existing baseline or start from config defaults
    if baseline_path.exists():
        baseline = load_yaml(baseline_path)
    else:
        baseline = {
            "schema_version": "2.0",
            "id": config_id,
            "product": config["product"],
            "platform": config["platform"],
            "compatibility": {"status": "unknown", "version_constraint": {"type": config["version_constraint"]["type"], "min": None, "max": None, "unsupported_examples": []}},
            "notes": {},
            "metadata": {"sources": [], "confidence": "low", "owner": "sre-team", "review_interval_days": 90, "ambiguous": True},
        }

    # Merge response into baseline
    updated = deep_merge(baseline, response)

    # Always update these on ingest
    updated["schema_version"] = "2.0"
    updated["id"] = config_id
    updated["metadata"]["ambiguous"] = False
    updated["metadata"]["last_reviewed"] = str(date.today())

    # Preserve structural fields from config
    if "type" not in updated.get("compatibility", {}).get("version_constraint", {}):
        updated.setdefault("compatibility", {}).setdefault("version_constraint", {})["type"] = \
            config["version_constraint"]["type"]

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with baseline_path.open("w") as f:
        yaml.safe_dump(updated, f, sort_keys=False, allow_unicode=True)

    print(f"[{config_id}] Baseline updated: {baseline_path}")
    print(f"  min={updated['compatibility']['version_constraint'].get('min')}")
    print(f"  max={updated['compatibility']['version_constraint'].get('max')}")
    print(f"  confidence={updated['metadata']['confidence']}")

    # Re-run diff and test generation
    scripts_dir = Path(__file__).parent
    for script in ["diff_rules.py", "generate_tests.py"]:
        result = subprocess.run(
            [sys.executable, str(scripts_dir / script), "--config-id", config_id],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"Warning: {script} exited with code {result.returncode}")

    print(f"\nDone. Next step:")
    print(f"  python scripts/create_pr.py --config-id {config_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest human review response into baseline rule")
    parser.add_argument("--config-id", required=True, help="Config ID to update")
    parser.add_argument("--review", required=True, type=Path, help="Path to completed response YAML")
    args = parser.parse_args()

    config_loader.load_config(args.config_id)
    ingest(args.config_id, args.review)


if __name__ == "__main__":
    main()
