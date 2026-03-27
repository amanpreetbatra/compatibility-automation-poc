# compatibility-automation-poc

Deterministic, auditable compatibility automation for any product and platform.

Query whether a software version is compatible, automatically extract bounds from vendor docs, and gate changes with a conservative safety policy. Uses VS Code Copilot for human-assisted review when automation is ambiguous.

---

## Quick start

```bash
pip install pyyaml requests

# Is veritas-infoscale compatible with this kernel?
python3 scripts/query.py --product veritas-infoscale --platform rhel --version 4.18.0-305.el8

# Run the full pipeline for one product/platform pair
python3 scripts/detect_changes.py --config-id veritas-infoscale_rhel
python3 scripts/extract_text.py   --config-id veritas-infoscale_rhel
python3 scripts/extract_envelope.py --config-id veritas-infoscale_rhel
python3 scripts/diff_rules.py     --config-id veritas-infoscale_rhel
python3 scripts/generate_tests.py --config-id veritas-infoscale_rhel
python3 scripts/create_pr.py      --config-id veritas-infoscale_rhel
```

---

## How it works

Each product+platform pair has a **config ID** (e.g., `veritas-infoscale_rhel`). A single YAML file in `configs/sources/` drives everything for that pair.

```
GitHub Actions (manual or weekly schedule)
  |
  |-- fetch_sources.py      Download vendor docs to data/{id}/raw/
  |-- detect_changes.py     Hash files, detect what changed -> pending.json
  |-- extract_text.py       Convert PDF/HTML to plain text
  |-- extract_envelope.py   Parse min/max version bounds (explicit only)
  |       |
  |       +-- HUMAN_REVIEW_NEEDED? -> human_review.py generates Copilot prompt
  |
  |-- diff_rules.py         Compare to baseline -> ALLOW or BLOCK
  |-- generate_tests.py     Build GO/NO_GO test cases
  |-- create_pr.py          Produce PR body with gating decision
  |-- Upload artifacts      rules/generated/, tests/generated/, human_reviews/
```

---

## File layout

```
configs/sources/{id}.yaml          One config per product+platform pair
data/{id}/raw/                     Fetched vendor docs (PDF, HTML, TXT)
data/{id}/parsed/                  Extracted text, manifests, diff summaries

rules/baselines/{id}.yaml          Authoritative baseline (schema v2.0)
rules/generated/{id}.yaml          Auto-extracted rule (pipeline output)

tests/baselines/{id}_cases.yaml    Hand-written test cases
tests/generated/{id}_cases.yaml    Auto-generated GO/NO_GO tests

human_reviews/{id}/                Copilot review prompts and response templates

scripts/
  lib/
    path_resolver.py               All file paths in one place
    config_loader.py               Load and validate configs
    version_compare.py             Generic version comparison (kernel, semver, package)
  query.py                         CLI compatibility query
  fetch_sources.py                 Download vendor docs
  detect_changes.py                Hash-based change detection
  extract_text.py                  Text extraction from raw docs
  extract_envelope.py              Parse version bounds from text
  diff_rules.py                    Compare generated vs baseline
  generate_tests.py                Generate test cases
  create_pr.py                     Generate PR body
  human_review.py                  Generate VS Code Copilot review request
  ingest_review.py                 Merge Copilot response into baseline
  migrate_legacy.py                One-time migration from old docs/ structure

.vscode/tasks.json                 VS Code tasks for common operations
.github/copilot-instructions.md    Copilot context for this repo
```

---

## Querying compatibility

```bash
# Basic query
python3 scripts/query.py \
  --product veritas-infoscale \
  --platform rhel \
  --version 4.18.0-305.el8

# Scope to specific versions
python3 scripts/query.py \
  --product veritas-infoscale --product-version 8.0.2 \
  --platform rhel --platform-version 8 \
  --version 4.18.0-477.el8

# Machine-readable JSON output
python3 scripts/query.py --product veritas-infoscale --platform rhel \
  --version 4.18.0-305.el8 --json
```

Exit codes: `0` = COMPATIBLE, `1` = NOT_COMPATIBLE, `2` = UNKNOWN

---

## Adding a new product or platform

1. Create `configs/sources/{id}.yaml`:

```yaml
id: oracle-db_rhel
product:
  name: oracle-db
  version: "19c"
platform:
  name: rhel
  version: "8"
version_constraint:
  type: semver                           # kernel_range | semver | package_version
  version_regex: '(\d+)\.(\d+)\.(\d+)'
  comparison_groups: [1, 2, 3]
sources:
  - name: oracle_cert_matrix_2026
    url: ""                              # URL to vendor doc
    type: vendor_hcl
    local_path: ""                       # or path to locally downloaded file
```

2. Create `rules/baselines/{id}.yaml` with known bounds (or leave for pipeline to discover).

3. Add the new `id` to `.vscode/tasks.json` under the `configId` input options.

4. Run the pipeline:
```bash
python3 scripts/fetch_sources.py --config-id oracle-db_rhel
python3 scripts/detect_changes.py --config-id oracle-db_rhel
# ... rest of pipeline
```

5. If no vendor docs are available yet, use the human review flow below.

---

## Human review with VS Code Copilot

When the pipeline cannot extract version bounds with high confidence, it prints `HUMAN_REVIEW_NEEDED` and you run:

```bash
python3 scripts/human_review.py --config-id veritas-infoscale_rhel
```

This creates two files in `human_reviews/{id}/`:
- `YYYY-MM-DD_review.md` — open in VS Code, paste the prompt into Copilot Chat
- `YYYY-MM-DD_response_template.yaml` — fill in with Copilot's answer

Then ingest the response:

```bash
python3 scripts/ingest_review.py \
  --config-id veritas-infoscale_rhel \
  --review human_reviews/veritas-infoscale_rhel/YYYY-MM-DD_response_template.yaml
```

This updates the baseline rule and re-runs diff and test generation automatically.

In VS Code, use **Terminal > Run Task** to access all common operations.

---

## Safety and gating

| Change | Decision |
|--------|----------|
| Envelope widening (lower min or higher max) | BLOCKED |
| Ambiguous extraction or low confidence | BLOCKED |
| Missing vendor source | BLOCKED |
| Envelope narrowing (higher min or lower max) | ALLOWED (risk-reducing) |
| Metadata-only change | INFO |

Only version bounds that appear **explicitly on the same line as a support statement** are accepted as high-confidence. Anything else is flagged ambiguous and requires human review via Copilot before it can be merged.

---

## Version constraint types

| Type | Example | Use case |
|------|---------|---------|
| `kernel_range` | `4.18.0-425.el8` | RHEL kernel upgrade windows |
| `semver` | `9.1.0` | Software package versions |
| `package_version` | `8.0.2-1.el8` | RPM/deb package releases |

---

## GitHub Actions

The workflow runs weekly (Monday 03:00 UTC) or on manual dispatch. It dynamically builds a matrix from all files in `configs/sources/` — adding a new product requires no workflow changes.

To run for a single config from the Actions UI:
1. Go to **Actions → Compatibility Update → Run workflow**
2. Enter the config ID (e.g., `veritas-infoscale_rhel`)

Each product/platform runs independently (`fail-fast: false`). Artifacts are uploaded per config ID.
