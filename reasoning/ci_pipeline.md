# CI Pipeline for Compatibility Knowledge Automation

## Overview
Automated, deterministic pipeline to ingest vendor compatibility documentation, extract kernel envelopes for Veritas 8.0.x on RHEL 8 (4.18.x), generate rules/reasoning/tests, and gate changes through PRs with human approval when compatibility changes or ambiguity is detected.

## Stages
1) **Detect changes**
   - Schedule fetch of vendor PCL, release notes, advisories.
   - Trigger on CMDB signal of new app version observed.
   - Compare doc versions and hashes; enqueue ingestion if changed.

2) **Acquire artifacts**
   - Download PDFs/HTML; record source URL, timestamp, hash.
   - Store raw text (deterministic extractor), hash, and provenance.

3) **Extract compatibility envelope (safe)**
   - Deterministic parsing with rules to capture explicit min/max kernel versions only when stated.
   - Capture verbatim quoted evidence with source ID and location.
   - Assign confidence: high (explicit bounds), medium (mapped via vendor table), low (ambiguous).
   - Ambiguity or missing bounds → mark "requires vendor clarification." No inferred widening.

4) **Generate artifacts**
   - Update `rules/*.yaml` (schema v1.1), `reasoning/*.md` (with quotes), `tests/*.yaml` (min, max, above-max, multi-app shape).
   - Include metadata: sources, confidence, owner, last_reviewed, review_interval_days.

5) **Validate**
   - Schema check for rules/tests.
   - Ensure references exist; ensure tests cover min/max/above-max per rule.
   - Run rule-diff safety algorithm (below).

6) **Publish via PR**
   - If no material change → no PR.
   - If change allowed → open PR with diff summary, evidence excerpts, and confidence.
   - Enforce human approval when envelope widens or confidence < high.

7) **Merge & notify**
   - After approval, merge to main; notify platform/ops; schedule downstream Ansible/FASTAPI reload if needed.

## Rule-Diff Safety Algorithm
Given old rule R_old and new rule R_new for the same app/OS:

- If `min` and `max` unchanged and only metadata/references updated → mark as informational; PR optional.
- If envelope narrows (new_min >= old_min and new_max <= old_max) → allow PR; label as risk-reducing.
- If envelope widens (new_min < old_min or new_max > old_max) → open PR but block auto-merge; require human approval with evidence review.
- If confidence drops (e.g., high→medium/low) or ambiguity flagged → block auto-merge; require manual review.
- If sources are missing or only internal observations present → block auto-merge; require vendor source.
- Always preserve unsupported_examples; adding new unsupported entries is allowed; removing unsupported entries is treated as widening and requires manual review.

Pseudocode sketch:
```
diff = compare(R_old.kernel, R_new.kernel)
confidence_ok = R_new.metadata.confidence == 'high'
has_vendor_source = any(src.type in ['vendor_hcl','release_notes','advisory'] for src in R_new.metadata.sources)

if diff.min == 0 and diff.max == 0:
    if metadata_only_changes:
        outcome = 'no_action'
    else:
        outcome = 'info_pr_ok'
elif R_new.kernel.min >= R_old.kernel.min and R_new.kernel.max <= R_old.kernel.max:
    outcome = 'pr_allowed_risk_reducing'
elif R_new.kernel.min < R_old.kernel.min or R_new.kernel.max > R_old.kernel.max:
    outcome = 'pr_block_auto_merge'
else:
    outcome = 'pr_block_auto_merge'

if not confidence_ok or not has_vendor_source or R_new.flags.ambiguous:
    outcome = 'pr_block_auto_merge'
```

## PR Creation & Enforcement
- CI opens PR with: rule diff summary (min/max changes), evidence quotes, confidence, reference list, and generated tests.
- Branch protection: require human review if outcome = pr_block_auto_merge or confidence < high or envelope widens.
- Label PRs: `compat-narrowing`, `compat-widening`, `compat-ambiguous` for governance tracking.

## Cadence
- Scheduled job aligns with `review_interval_days` (e.g., 90). If past due, CI revalidates docs and opens PR even if unchanged to refresh last_reviewed metadata.
