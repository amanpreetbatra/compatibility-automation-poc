#!/usr/bin/env python3
"""Generate test cases from kernel envelopes (min, max, above-max, multi-app shape)."""

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # type: ignore

GEN_RULE_DIR = Path("rules/_generated")
TEST_OUT_DIR = Path("tests/_generated")

KERNEL_NUM = re.compile(r"4\.18\.0-(\d+)\.el8")


def load_rule(path: Path) -> Dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def bump_kernel(k: str) -> Optional[str]:
    m = KERNEL_NUM.search(k)
    if not m:
        return None
    num = int(m.group(1)) + 1
    return f"4.18.0-{num}.el8"


def build_tests(rule: Dict) -> List[Dict]:
    app = rule.get("application", {})
    name = app.get("name", "app")
    version = app.get("version", "0.0.0")
    min_k = rule.get("kernel", {}).get("min")
    max_k = rule.get("kernel", {}).get("max")
    tests: List[Dict] = []

    if min_k and max_k:
        tests.append(
            {
                "id": f"go-{name}-{max_k}",
                "description": "Upgrade within certified envelope",
                "os": "rhel8",
                "current_kernel": min_k,
                "target_kernel": max_k,
                "applications": [{"name": name, "version": version}],
                "expected": {
                    "decision": "GO",
                    "highest_supported_kernel": max_k,
                    "blocking_applications": [],
                },
                "rationale": f"Target kernel at documented upper bound for {name} {version}.",
            }
        )

        above = bump_kernel(max_k)
        if above:
            tests.append(
                {
                    "id": f"no-go-{name}-{above}",
                    "description": "Upgrade beyond certified upper bound",
                    "os": "rhel8",
                    "current_kernel": min_k,
                    "target_kernel": above,
                    "applications": [{"name": name, "version": version}],
                    "expected": {
                        "decision": "NO_GO",
                        "highest_supported_kernel": max_k,
                        "blocking_applications": [name],
                    },
                    "rationale": f"{above} outside documented envelope; cap at {max_k}.",
                }
            )

    return tests


def main() -> None:
    if not GEN_RULE_DIR.exists():
        print("No generated rules found; skipping test generation")
        return

    TEST_OUT_DIR.mkdir(parents=True, exist_ok=True)

    for rule_path in GEN_RULE_DIR.glob("*.yaml"):
        rule = load_rule(rule_path)
        tests = build_tests(rule)
        if not tests:
            print(f"No tests generated for {rule_path}")
            continue
        out_path = TEST_OUT_DIR / rule_path.name.replace(".yaml", "_tests.yaml")
        with out_path.open("w") as f:
            yaml.safe_dump(tests, f, sort_keys=False)
        print(f"Wrote tests to {out_path}")


if __name__ == "__main__":
    main()
