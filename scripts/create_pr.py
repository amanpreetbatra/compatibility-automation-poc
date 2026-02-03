#!/usr/bin/env python3
"""Create PR with rule/reasoning/test changes and evidence summary; enforce gating labels.

This script prepares a PR body and gating decision based on diff_summary.json.
It does not call GitHub directly; wire to gh CLI or API in CI where credentials exist.
"""

import json
from pathlib import Path
from typing import Dict

SUMMARY_FILE = Path("docs/parsed/diff_summary.json")
PR_BODY_FILE = Path("docs/parsed/pr_body.md")


def load_summary() -> Dict:
    if not SUMMARY_FILE.exists():
        return {}
    with SUMMARY_FILE.open() as f:
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
    lines = ["## Compatibility Update", "", f"Gate: {gate}", ""]
    lines.append("| Rule | Decision | Reason | Old min | Old max | New min | New max | Confidence | Ambiguous |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for rule, data in summary.items():
        lines.append(
            "| {rule} | {decision} | {reason} | {old_min} | {old_max} | {new_min} | {new_max} | {confidence} | {ambiguous} |".format(
                rule=rule,
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
    return "\n".join(lines)


def main() -> None:
    summary = load_summary()
    gate = classify(summary)
    body = build_body(summary, gate)

    PR_BODY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PR_BODY_FILE.write_text(body)
    print(f"Prepared PR body at {PR_BODY_FILE} with gate={gate}")
    if gate == "no_changes":
        print("No changes detected; skip PR creation")
    elif gate == "pr_block_auto_merge":
        print("Auto-merge must be blocked; require human review")
    else:
        print("PR can be opened; apply branch protection as configured")


if __name__ == "__main__":
    main()
