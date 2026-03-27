# Copilot Instructions: Compatibility Automation Tool

This repository automates software compatibility tracking across any product and platform.
Use this context when helping with code, reviewing vendor docs, or filling in review templates.

---

## What This Tool Does

Given a vendor document (HCL, release notes, advisory), it extracts:
- The **minimum** and **maximum** supported version for a product on a platform
- Confidence level of the extraction (high / medium / low)
- Whether the change is **safe to auto-merge** (narrowing) or requires **human review** (widening/ambiguous)

It then answers queries like:
> "Is veritas-infoscale 8.0.2 compatible with rhel 8 kernel 4.18.0-305.el8?"

---

## Key Concepts

### Config ID
Each product+platform pair has a unique ID (e.g., `veritas-infoscale_rhel`).
Config lives in `configs/sources/{id}.yaml`.

### Version Constraint Types
| Type | Example version | Used for |
|------|----------------|---------|
| `kernel_range` | `4.18.0-425.el8` | RHEL-style kernel upgrades |
| `semver` | `9.1.0` | Software packages |
| `package_version` | `8.0.2-1.el8` | RPM/deb packages |

### Rule Schema v2.0 (in `rules/baselines/{id}.yaml`)
```yaml
schema_version: "2.0"
id: veritas-infoscale_rhel
product:
  name: veritas-infoscale
  version: "8.0.2"
platform:
  name: rhel
  version: "8"
compatibility:
  status: supported            # supported | unsupported | partial | unknown
  version_constraint:
    type: kernel_range
    min: 4.18.0-193.el8        # earliest supported version
    max: 4.18.0-425.el8        # latest supported version
    unsupported_examples:
      - 4.18.0-477.el8
notes:
  risk: "..."
  remediation: "..."
metadata:
  sources:
    - name: "Veritas HCL Oct 2023"
      reference: "PCL-8.0.2-Oct2023"
      type: vendor_hcl          # vendor_hcl | release_notes | advisory | internal
  confidence: medium            # high | medium | low | unknown
  owner: sre-team
  last_reviewed: "2026-01-30"
  review_interval_days: 90
  ambiguous: false
```

### Gating Rules
- **Widening** (lower min or higher max than baseline) → **BLOCKED**
- **Ambiguous or low confidence** → **BLOCKED**
- **Narrowing** (higher min or lower max) → **ALLOWED** (risk-reducing)
- **Metadata-only change** → INFO

---

## When Reviewing Vendor Docs (Human Review)

You will receive a prompt asking you to analyze a vendor document. Follow these rules:

1. **Only report what is explicitly documented.** Do not infer or extrapolate.
2. **Extract exact version strings** that match the `version_regex` in the config.
3. **Cite your source** (document title, section, page number or URL).
4. If a supported range is not clearly stated, set `status: unknown`.
5. Do not reference AI model knowledge — only what appears in the provided documents.

### Expected Output Format
When asked to produce a compatibility review, output **only** this YAML:
```yaml
compatibility:
  status: supported
  version_constraint:
    min: ""
    max: ""
    unsupported_examples: []
notes:
  risk: ""
  remediation: ""
metadata:
  sources:
    - name: ""
      reference: ""
      type: vendor_hcl
  confidence: high
```

---

## File Layout
```
configs/sources/{id}.yaml        ← config per product+platform pair
data/{id}/raw/                   ← fetched vendor docs
data/{id}/parsed/                ← extracted text + manifests
rules/baselines/{id}.yaml        ← authoritative baseline rule
rules/generated/{id}.yaml        ← auto-extracted (pipeline output)
tests/baselines/{id}_cases.yaml  ← hand-written test cases
tests/generated/{id}_cases.yaml  ← auto-generated test cases
human_reviews/{id}/              ← Copilot review requests & responses
scripts/lib/                     ← shared library (path_resolver, config_loader, version_compare)
```

## Adding a New Product

1. Create `configs/sources/{new-id}.yaml` with product/platform/version_regex
2. Add any vendor doc URLs or local files to `sources:` in the config
3. Create `rules/baselines/{new-id}.yaml` with known compatibility bounds
4. Add `"{new-id}"` to the `options` array in `.vscode/tasks.json`
5. Run: `python scripts/fetch_sources.py --config-id {new-id}`
6. Run: `python scripts/query.py --product ... --platform ... --version ...`
