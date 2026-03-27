#!/usr/bin/env python3
"""One-time migration: convert old docs/ structure to the new generic data/ structure.

Run once, then commit the results. The old docs/ paths are preserved with .gitkeep
so no existing CI references break during transition.

Usage:
  python scripts/migrate_legacy.py
"""

import json
import shutil
import sys
from pathlib import Path

import yaml  # type: ignore

REPO_ROOT = Path(__file__).parent.parent


def migrate() -> None:
    config_id = "veritas-infoscale_rhel"
    old_raw = REPO_ROOT / "docs" / "raw"
    old_parsed = REPO_ROOT / "docs" / "parsed"
    new_raw = REPO_ROOT / "data" / config_id / "raw"
    new_parsed = REPO_ROOT / "data" / config_id / "parsed"

    # 1. Copy docs/raw/* to data/{id}/raw/
    new_raw.mkdir(parents=True, exist_ok=True)
    if old_raw.exists():
        for src in old_raw.rglob("*"):
            if src.is_file() and src.name != ".gitkeep":
                dest = new_raw / src.relative_to(old_raw)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                print(f"  Copied {src} -> {dest}")
    print(f"[1] Migrated docs/raw/ -> data/{config_id}/raw/")

    # 2. Copy docs/parsed/* to data/{id}/parsed/
    new_parsed.mkdir(parents=True, exist_ok=True)
    if old_parsed.exists():
        for src in old_parsed.rglob("*"):
            if src.is_file() and src.name != ".gitkeep":
                dest = new_parsed / src.relative_to(old_parsed)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                print(f"  Copied {src} -> {dest}")
    print(f"[2] Migrated docs/parsed/ -> data/{config_id}/parsed/")

    # 3. Convert rules/veritas_802_rhel8.yaml to v2.0 schema at rules/baselines/{id}.yaml
    old_rule = REPO_ROOT / "rules" / "veritas_802_rhel8.yaml"
    new_baseline = REPO_ROOT / "rules" / "baselines" / f"{config_id}.yaml"
    if old_rule.exists() and not new_baseline.exists():
        with old_rule.open() as f:
            old = yaml.safe_load(f) or {}
        new_rule = {
            "schema_version": "2.0",
            "id": config_id,
            "product": {
                "name": old.get("application", {}).get("name", "veritas-infoscale"),
                "version": str(old.get("application", {}).get("version", "8.0.2")),
            },
            "platform": {
                "name": old.get("os", {}).get("family", "rhel"),
                "version": str(old.get("os", {}).get("major_version", "8")),
            },
            "compatibility": {
                "status": "supported",
                "version_constraint": {
                    "type": "kernel_range",
                    "min": old.get("kernel", {}).get("min"),
                    "max": old.get("kernel", {}).get("max"),
                    "unsupported_examples": old.get("kernel", {}).get("unsupported_examples", []),
                },
            },
            "notes": old.get("notes", {}),
            "metadata": {
                **old.get("metadata", {}),
                "ambiguous": False,
            },
        }
        new_baseline.parent.mkdir(parents=True, exist_ok=True)
        with new_baseline.open("w") as f:
            yaml.safe_dump(new_rule, f, sort_keys=False)
        print(f"[3] Converted {old_rule} -> {new_baseline} (schema v2.0)")
    elif new_baseline.exists():
        print(f"[3] Skipped: {new_baseline} already exists")

    # 4. Migrate test cases
    old_tests = REPO_ROOT / "tests" / "veritas_802_kernel_cases.yaml"
    new_tests = REPO_ROOT / "tests" / "baselines" / f"{config_id}_cases.yaml"
    if old_tests.exists() and not new_tests.exists():
        new_tests.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_tests, new_tests)
        print(f"[4] Copied {old_tests} -> {new_tests}")
    elif new_tests.exists():
        print(f"[4] Skipped: {new_tests} already exists")

    # 5. Ensure human_reviews dir exists
    hr_dir = REPO_ROOT / "human_reviews" / config_id
    hr_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = hr_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"[5] Created {hr_dir}/")

    print("\nMigration complete.")
    print("Old docs/ paths are preserved. Remove them after verifying CI passes.")
    print(f"\nTest with:")
    print(f"  python scripts/query.py --product veritas-infoscale --platform rhel --version 4.18.0-305.el8")


if __name__ == "__main__":
    migrate()
