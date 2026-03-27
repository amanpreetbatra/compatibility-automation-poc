#!/usr/bin/env python3
"""Generate test cases from compatibility envelopes (min, max, above-max)."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver
from lib.version_compare import VersionComparator


def load_rule(path: Path) -> Dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _get_bounds(rule: Dict):
    """Extract min/max from rule, supporting both schema v2.0 and v1.1 (legacy)."""
    vc = rule.get("compatibility", {}).get("version_constraint", {})
    if vc:
        return vc.get("min"), vc.get("max")
    kernel = rule.get("kernel", {})
    return kernel.get("min"), kernel.get("max")


def build_tests(rule: Dict, comparator: VersionComparator) -> List[Dict]:
    # Support both v2.0 and v1.1 schema
    product = rule.get("product") or rule.get("application") or {}
    platform = rule.get("platform") or rule.get("os") or {}
    name = product.get("name", "app")
    version = product.get("version", "0.0.0")
    platform_name = platform.get("name", "")
    platform_version = platform.get("version", "")
    platform_label = f"{platform_name}{platform_version}"

    min_v, max_v = _get_bounds(rule)
    tests: List[Dict] = []

    if min_v and max_v:
        tests.append(
            {
                "id": f"go-{name}-{max_v}",
                "description": "Upgrade within certified envelope",
                "platform": platform_label,
                "current_version": min_v,
                "target_version": max_v,
                "applications": [{"name": name, "version": version}],
                "expected": {
                    "decision": "GO",
                    "highest_supported_version": max_v,
                    "blocking_applications": [],
                },
                "rationale": f"Target version at documented upper bound for {name} {version}.",
            }
        )

        try:
            above = comparator.bump(max_v)
            tests.append(
                {
                    "id": f"no-go-{name}-{above}",
                    "description": "Upgrade beyond certified upper bound",
                    "platform": platform_label,
                    "current_version": min_v,
                    "target_version": above,
                    "applications": [{"name": name, "version": version}],
                    "expected": {
                        "decision": "NO_GO",
                        "highest_supported_version": max_v,
                        "blocking_applications": [name],
                    },
                    "rationale": f"{above} outside documented envelope; cap at {max_v}.",
                }
            )
        except ValueError:
            pass

    return tests


def run_for_config(config_id: str) -> None:
    config = config_loader.load_config(config_id)
    comparator = VersionComparator(config["version_constraint"])
    gen_rule_path = path_resolver.generated_rule(config_id)
    out_path = path_resolver.generated_tests(config_id)

    if not gen_rule_path.exists():
        print(f"[{config_id}] No generated rule found; skipping test generation")
        return

    rule = load_rule(gen_rule_path)
    tests = build_tests(rule, comparator)
    if not tests:
        print(f"[{config_id}] No tests generated (rule may be ambiguous)")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        yaml.safe_dump(tests, f, sort_keys=False)
    print(f"[{config_id}] Wrote {len(tests)} tests to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test cases from compatibility rules")
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
