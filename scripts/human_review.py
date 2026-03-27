#!/usr/bin/env python3
"""Generate a VS Code Copilot Chat review request when automated extraction is ambiguous.

Creates two files in human_reviews/{config-id}/:
  YYYY-MM-DD_review.md               — paste this prompt into VS Code Copilot Chat
  YYYY-MM-DD_response_template.yaml  — fill in with Copilot's answer

Then run:
  python scripts/ingest_review.py --config-id <id> --review <response_template.yaml>
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional

import yaml  # type: ignore

sys.path.insert(0, str(Path(__file__).parent))
from lib import config_loader, path_resolver


def load_generated_rule(config_id: str) -> Optional[Dict]:
    path = path_resolver.generated_rule(config_id)
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_baseline_rule(config_id: str) -> Optional[Dict]:
    path = path_resolver.baseline_rule(config_id)
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _get_bounds(rule: Optional[Dict]):
    if not rule:
        return None, None
    vc = rule.get("compatibility", {}).get("version_constraint", {})
    if vc:
        return vc.get("min"), vc.get("max")
    return None, None


def generate_review(config_id: str) -> None:
    config = config_loader.load_config(config_id)
    generated = load_generated_rule(config_id)
    baseline = load_baseline_rule(config_id)

    product = config["product"]
    platform = config["platform"]
    vc = config["version_constraint"]
    today = date.today().isoformat()

    review_dir = path_resolver.human_review_dir(config_id)
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / f"{today}_review.md"
    template_path = review_dir / f"{today}_response_template.yaml"

    # Gather context from generated rule if available
    gen_min, gen_max = _get_bounds(generated)
    gen_confidence = generated.get("metadata", {}).get("confidence", "unknown") if generated else "unknown"
    gen_evidence = generated.get("notes", {}).get("evidence", "none") if generated else "none"
    base_min, base_max = _get_bounds(baseline)

    # Build current baseline defaults for the template
    base_sources = []
    if baseline:
        base_sources = baseline.get("metadata", {}).get("sources", [])

    prompt_content = f"""# Compatibility Review Request: {config_id}

Generated: {today}
Automated extraction confidence: **{gen_confidence}**
Evidence found by automation: `{gen_evidence}`

---

## Instructions

1. Open this file in VS Code
2. Open Copilot Chat (`Ctrl+Shift+I` / `Cmd+Shift+I`)
3. Paste the prompt below into Copilot Chat (optionally attach the vendor doc)
4. Copy Copilot's YAML response into the response template file:
   `{template_path.name}`
5. Run:
   ```
   python scripts/ingest_review.py --config-id {config_id} --review {template_path}
   ```

---

## Copilot Chat Prompt

```
You are an enterprise infrastructure compatibility analyst.

Task: Analyze vendor documentation to extract the supported version range for:
  Product:  {product['name']} {product['version']}
  Platform: {platform['name']} {platform['version']}

Version format: {vc['version_regex']}
(Example versions match this pattern — only extract versions that match.)

Context from automated extraction:
  Automation confidence: {gen_confidence}
  Evidence found: {gen_evidence}
  Current baseline: min={base_min or 'unknown'}, max={base_max or 'unknown'}

Rules:
- Only report what is EXPLICITLY documented. Do not infer or extrapolate.
- If a range is not clearly stated, mark status as "unknown" or "partial".
- List any versions that are explicitly stated as NOT supported.
- Cite the specific document section/page for each finding.

Output ONLY this YAML block (no other text):

compatibility:
  status: supported        # supported | unsupported | partial | unknown
  version_constraint:
    min: ""                # earliest supported version (exact string from docs)
    max: ""                # latest supported version (exact string from docs)
    unsupported_examples:
      - ""                 # versions explicitly listed as unsupported
notes:
  risk: ""                 # operational risk of running outside the envelope
  remediation: ""          # recommended action
metadata:
  sources:
    - name: ""             # document title
      reference: ""        # section, page, or URL
      type: vendor_hcl     # vendor_hcl | release_notes | advisory | internal
  confidence: high         # high | medium | low
```

---

## Context

Product: {product['name']} {product['version']}
Platform: {platform['name']} {platform['version']}
Version regex: `{vc['version_regex']}`
Current baseline min: `{base_min or 'not set'}`
Current baseline max: `{base_max or 'not set'}`
"""

    review_path.write_text(prompt_content)
    print(f"[{config_id}] Created review request: {review_path}")

    # Build response template pre-filled with current values
    template = {
        "compatibility": {
            "status": baseline.get("compatibility", {}).get("status", "unknown") if baseline else "unknown",
            "version_constraint": {
                "min": base_min or "",
                "max": base_max or "",
                "unsupported_examples": (
                    baseline.get("compatibility", {}).get("version_constraint", {}).get("unsupported_examples", [])
                    if baseline else []
                ),
            },
        },
        "notes": {
            "risk": config.get("notes", {}).get("risk", ""),
            "remediation": config.get("notes", {}).get("remediation", ""),
        },
        "metadata": {
            "sources": base_sources or [],
            "confidence": "high",
        },
    }

    with template_path.open("w") as f:
        yaml.safe_dump(template, f, sort_keys=False, allow_unicode=True)
    print(f"[{config_id}] Created response template: {template_path}")

    print(f"""
Next steps:
  1. Open in VS Code:  code "{review_path}"
  2. Paste prompt into Copilot Chat and fill in: "{template_path}"
  3. Run: python scripts/ingest_review.py --config-id {config_id} --review "{template_path}"
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate human review request for VS Code Copilot")
    parser.add_argument("--config-id", required=True, help="Config ID to generate review for")
    args = parser.parse_args()

    config_loader.load_config(args.config_id)
    generate_review(args.config_id)


if __name__ == "__main__":
    main()
