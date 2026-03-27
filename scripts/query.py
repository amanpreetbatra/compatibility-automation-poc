#!/usr/bin/env python3
"""Query compatibility: is product X version Y compatible with platform P version V?

Usage examples:
  python scripts/query.py --product veritas-infoscale --platform rhel --version 4.18.0-305.el8
  python scripts/query.py --product veritas-infoscale --product-version 8.0.2 \\
      --platform rhel --platform-version 8 --version 4.18.0-477.el8
  python scripts/query.py --product veritas-infoscale --platform rhel \\
      --version 4.18.0-305.el8 --json

Exit codes:
  0  COMPATIBLE
  1  NOT_COMPATIBLE
  2  UNKNOWN (no rule found or status is unknown)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver
from lib.version_compare import VersionComparator


def load_baseline(config_id: str) -> Optional[Dict]:
    path = path_resolver.baseline_rule(config_id)
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _get_bounds(rule: Dict):
    vc = rule.get("compatibility", {}).get("version_constraint", {})
    if vc:
        return vc.get("min"), vc.get("max")
    kernel = rule.get("kernel", {})
    return kernel.get("min"), kernel.get("max")


def find_matching_configs(
    product: str,
    platform: str,
    product_version: Optional[str],
    platform_version: Optional[str],
) -> List[Dict]:
    all_configs = config_loader.load_all_configs()
    matches = []
    for cfg in all_configs.values():
        p = cfg.get("product", {})
        pl = cfg.get("platform", {})
        if p.get("name", "").lower() != product.lower():
            continue
        if pl.get("name", "").lower() != platform.lower():
            continue
        if product_version and p.get("version", "") != product_version:
            continue
        if platform_version and pl.get("version", "") != platform_version:
            continue
        matches.append(cfg)
    return matches


def query(
    product: str,
    platform: str,
    version: str,
    product_version: Optional[str] = None,
    platform_version: Optional[str] = None,
) -> Dict:
    matching = find_matching_configs(product, platform, product_version, platform_version)

    if not matching:
        return {
            "result": "UNKNOWN",
            "reason": "no_rule_found",
            "message": (
                f"No compatibility rule found for product='{product}' platform='{platform}'.\n"
                f"To add one:\n"
                f"  1. Create configs/sources/<id>.yaml with product/platform details\n"
                f"  2. Add vendor doc sources\n"
                f"  3. Run: python scripts/fetch_sources.py && python scripts/detect_changes.py"
            ),
            "product": product,
            "product_version": product_version,
            "platform": platform,
            "platform_version": platform_version,
            "checked_version": version,
        }

    results = []
    for cfg in matching:
        config_id = cfg["id"]
        rule = load_baseline(config_id)
        if not rule:
            results.append({
                "config_id": config_id,
                "result": "UNKNOWN",
                "reason": "no_baseline_rule",
                "message": f"Config '{config_id}' exists but no baseline rule found. Run the pipeline to generate one.",
            })
            continue

        status = rule.get("compatibility", {}).get("status", "unknown")
        if status == "unsupported":
            results.append({
                "config_id": config_id,
                "result": "NOT_COMPATIBLE",
                "reason": "status_unsupported",
                "product": cfg["product"],
                "platform": cfg["platform"],
                "checked_version": version,
                "confidence": rule.get("metadata", {}).get("confidence"),
                "sources": rule.get("metadata", {}).get("sources", []),
            })
            continue

        min_v, max_v = _get_bounds(rule)
        if not min_v or not max_v:
            results.append({
                "config_id": config_id,
                "result": "UNKNOWN",
                "reason": "no_version_bounds",
                "message": (
                    f"Rule '{config_id}' exists but has no version bounds. "
                    f"Run the pipeline or provide a human review:\n"
                    f"  python scripts/human_review.py --config-id {config_id}"
                ),
            })
            continue

        comparator = VersionComparator(cfg["version_constraint"])
        try:
            compatible = comparator.is_within(version, min_v, max_v)
        except ValueError as e:
            results.append({
                "config_id": config_id,
                "result": "UNKNOWN",
                "reason": "version_parse_error",
                "message": str(e),
            })
            continue

        results.append({
            "config_id": config_id,
            "result": "COMPATIBLE" if compatible else "NOT_COMPATIBLE",
            "reason": "within_envelope" if compatible else "outside_envelope",
            "product": cfg["product"],
            "platform": cfg["platform"],
            "checked_version": version,
            "min_version": min_v,
            "max_version": max_v,
            "confidence": rule.get("metadata", {}).get("confidence"),
            "ambiguous": rule.get("metadata", {}).get("ambiguous", False),
            "sources": rule.get("metadata", {}).get("sources", []),
        })

    if not results:
        return {
            "result": "UNKNOWN",
            "reason": "no_results",
            "checked_version": version,
        }

    # If any result is NOT_COMPATIBLE, the overall result is NOT_COMPATIBLE
    overall = "COMPATIBLE"
    for r in results:
        if r["result"] == "NOT_COMPATIBLE":
            overall = "NOT_COMPATIBLE"
            break
        if r["result"] == "UNKNOWN":
            overall = "UNKNOWN"

    return {"result": overall, "details": results}


def print_human(result: Dict) -> None:
    overall = result.get("result", "UNKNOWN")
    print(f"\n{'='*50}")
    print(f"  Result: {overall}")
    print(f"{'='*50}")

    if "message" in result:
        print(f"\n{result['message']}\n")
        return

    for detail in result.get("details", []):
        print(f"\n  Config:   {detail.get('config_id', '')}")
        prod = detail.get("product", {})
        plat = detail.get("platform", {})
        if prod:
            print(f"  Product:  {prod.get('name')} {prod.get('version')}")
        if plat:
            print(f"  Platform: {plat.get('name')} {plat.get('version')}")
        print(f"  Checked:  {detail.get('checked_version')}")

        if detail.get("min_version"):
            print(f"  Range:    {detail['min_version']} to {detail['max_version']}")
        if detail.get("confidence"):
            print(f"  Confidence: {detail['confidence']}")
        if detail.get("ambiguous"):
            print(f"  Warning: rule is marked ambiguous — run human review for higher confidence")
        if detail.get("message"):
            print(f"  Note: {detail['message']}")

        sources = detail.get("sources", [])
        if sources:
            print(f"  Sources:")
            for s in sources:
                print(f"    - {s.get('name')} ({s.get('type')})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query compatibility for a product/platform version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--product", required=True, help="Product name (e.g. veritas-infoscale)")
    parser.add_argument("--product-version", help="Product version (e.g. 8.0.2)")
    parser.add_argument("--platform", required=True, help="Platform name (e.g. rhel)")
    parser.add_argument("--platform-version", help="Platform version (e.g. 8)")
    parser.add_argument("--version", required=True, help="Version to check (e.g. 4.18.0-305.el8)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = query(
        product=args.product,
        platform=args.platform,
        version=args.version,
        product_version=args.product_version,
        platform_version=args.platform_version,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human(result)

    overall = result.get("result", "UNKNOWN")
    if overall == "COMPATIBLE":
        sys.exit(0)
    elif overall == "NOT_COMPATIBLE":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
