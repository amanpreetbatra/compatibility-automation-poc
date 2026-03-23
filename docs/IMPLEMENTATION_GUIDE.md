# AI-Powered Compatibility Pipeline Implementation Guide

## Problem statement
Monthly OS patching for enterprise applications like Veritas InfoScale on RHEL 8 is still often a manual control. Engineers have to read product compatibility lists, release notes, and errata advisories, then compare them against planned kernels. That process is slow, inconsistent, and hard to audit at banking scale.

## Solution overview
This PoC turns that manual review into a local-first compatibility pipeline:

- source documents are staged or fetched into `docs/raw/`
- document hashes drive change detection
- parsed text is analyzed by a deterministic regex path and, when enabled, by GitHub Models
- AI output is validated against the expected RHEL 8 kernel regex before it can influence rule generation
- a generated compatibility rule is compared against the baseline rule
- GO/NO_GO test cases and an HTML dashboard provide the demo output

The control objective is conservative by design: the pipeline can surface evidence and reduce analyst effort, but it never auto-approves a widened or ambiguous compatibility envelope.

## Quick start
```bash
pip install pyyaml
python run_demo.py --offline
```

This runs the full demo without any external API access and produces `dashboard.html` plus generated rule, diff, and test artifacts.

## Enable AI mode
GitHub Models works here because it only needs a GitHub personal access token with `models: read` scope.

You can export variables directly, or copy `.env.example` to `.env` and set them there. The demo runner and AI analysis script both load `.env` automatically.

```bash
export GITHUB_TOKEN=ghp_your_token_here
python run_demo.py
```

Optional:

```bash
export GITHUB_MODEL=openai/gpt-4o
```

The pipeline calls:

- endpoint: `https://models.github.ai/inference/chat/completions`
- auth header: `Authorization: Bearer <GITHUB_TOKEN>`
- API version header: `X-GitHub-Api-Version: 2022-11-28`
- accept header: `Accept: application/vnd.github+json`

## Safety design
- AI never auto-approves a change on its own.
- AI-extracted kernels must match `4\.18\.0-\d+\.el8` or they are rejected.
- If AI is unavailable, the pipeline falls back to regex extraction.
- Widening the support envelope always blocks automatic approval.
- Low confidence always blocks.
- Ambiguous output always blocks.
- Every step writes auditable artifacts under `docs/parsed/`, `rules/_generated/`, or `tests/_generated/`.

## Gating rules
| Extracted outcome | Gate | Meaning |
| --- | --- | --- |
| unchanged envelope | `info` | No compatibility change detected |
| narrowed envelope | `pr_allowed_risk_reducing` | Safer restriction; still reviewable |
| widened envelope | `pr_block_auto_merge` | Block and require human approval |
| low confidence | `pr_block_auto_merge` | Block because evidence is insufficient |
| ambiguous | `pr_block_auto_merge` | Block because support is not decisive |

## GitHub Models API
The implementation uses GitHub's REST inference endpoint documented here:

- [GitHub REST API for Models inference](https://docs.github.com/en/rest/models/inference)

As of March 23, 2026, GitHub's public docs and model catalog describe free usage limits that vary by model tier; for high-tier models such as `openai/gpt-4o`, the commonly documented free limit is 50 requests per day. Treat that number as operational guidance for this demo, not a permanent contract, because GitHub can change limits without notice.

## Deployment options
- Cron on an internal Linux server that fetches docs, runs the pipeline, and publishes the dashboard to an internal share.
- Manual pre-patch execution by the platform team before each monthly RHEL patch window.
- Git-based workflow where the generated rule and test deltas are reviewed through normal pull request controls, even without GitHub Actions.

## Extend to more applications
- add additional baseline rules in `rules/`
- add source definitions in `docs/sources.yaml`
- create application-specific prompts in `prompts/`
- expand extraction logic for different kernel families, package versions, firmware, or middleware dependencies
- add more demo or production documents under `demo/sample_vendor_docs/` or fetched sources

## File structure overview
```text
demo/sample_vendor_docs/        Demo vendor text used for offline runs
docs/raw/                       Raw fetched or staged documents
docs/parsed/                    Parsed text and JSON provenance artifacts
docs/sources.yaml               Vendor source configuration
prompts/                        System prompt for AI analysis
rules/                          Baseline compatibility rules
rules/_generated/               Generated rule output
scripts/fetch_sources.py        Vendor document downloader
scripts/analyze_with_ai.py      GitHub Models analysis step
scripts/extract_envelope.py     AI-first envelope extraction with regex fallback
tests/_generated/               Generated GO/NO_GO test cases
run_demo.py                     End-to-end demo entry point
dashboard.html                  Demo dashboard output
```
