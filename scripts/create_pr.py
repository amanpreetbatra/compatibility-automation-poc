#!/usr/bin/env python3
"""Create PR body with rule/test changes and evidence summary; enforce gating labels.

This script prepares a PR body and gating decision based on diff_summary.json.
It does not call GitHub directly; wire to gh CLI or API in CI where credentials exist.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def load_summary(summary_file: Path) -> Dict:
    if not summary_file.exists():
        return {}
    with summary_file.open() as f:
        return json.load(f)


def classify(summary: Dict) -> str:
    if not summary:
        return "no_changes"
    decisions = {item.get("decision") for item in summary.values()}
    if "pr_block_auto_merge" in decisions:
        return "pr_block_auto_merge"
    if decisions == {"info"}:
        return "info"
    return "pr_allowed"


def build_body(summary: Dict, gate: str) -> str:
    lines = ["## Compatibility Update", "", f"Gate: **{gate}**", ""]
    lines.append("| Config | Decision | Reason | Old min | Old max | New min | New max | Confidence | Ambiguous |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for config_id, data in summary.items():
        lines.append(
            "| {config} | {decision} | {reason} | {old_min} | {old_max} | {new_min} | {new_max} | {confidence} | {ambiguous} |".format(
                config=config_id,
                decision=data.get("decision"),
                reason=data.get("reason"),
                old_min=data.get("old_min"),
                old_max=data.get("old_max"),
                new_min=data.get("new_min"),
                new_max=data.get("new_max"),
                confidence=data.get("confidence"),
                ambiguous=data.get("ambiguous"),
            )
        )
    lines.append("")
    lines.append("Review requirements:")
    lines.append("- Widening or low confidence or ambiguous → manual approval required.")
    lines.append("- Narrowing with high confidence can be approved per policy.")
    lines.append("")
    lines.append("---")
    lines.append(
        "If `HUMAN_REVIEW_NEEDED` was printed during extraction, download the review file from "
        "CI artifacts and follow the Copilot Chat instructions in `human_reviews/{config-id}/`."
    )
    return "\n".join(lines)


def run_for_config(config_id: str) -> Dict:
    summary_file = path_resolver.diff_summary(config_id)
    pr_body_file = path_resolver.pr_body(config_id)

    summary = load_summary(summary_file)
    gate = classify(summary)
    body = build_body(summary, gate)

    pr_body_file.parent.mkdir(parents=True, exist_ok=True)
    pr_body_file.write_text(body)
    print(f"[{config_id}] Prepared PR body at {pr_body_file} gate={gate}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PR body from diff summary")
    parser.add_argument("--config-id", help="Process a single config ID (default: all)")
    args = parser.parse_args()

    all_summaries: Dict = {}
    if args.config_id:
        config_loader.load_config(args.config_id)
        all_summaries = run_for_config(args.config_id)
    else:
        for config_id in config_loader.list_config_ids():
            all_summaries.update(run_for_config(config_id))

    gate = classify(all_summaries)
    if gate == "no_changes":
        print("No changes detected; skip PR creation")
    elif gate == "pr_block_auto_merge":
        print("Auto-merge must be blocked; require human review")
    else:
        print("PR can be opened; apply branch protection as configured")


if __name__ == "__main__":
    main()
