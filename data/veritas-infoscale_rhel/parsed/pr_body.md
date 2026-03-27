## Compatibility Update

Gate: **pr_block_auto_merge**

| Config | Decision | Reason | Old min | Old max | New min | New max | Confidence | Ambiguous |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| veritas-infoscale_rhel | pr_block_auto_merge | ambiguous | 4.18.0-193.el8 | 4.18.0-425.el8 | None | None | low | True |

Review requirements:
- Widening or low confidence or ambiguous → manual approval required.
- Narrowing with high confidence can be approved per policy.

---
If `HUMAN_REVIEW_NEEDED` was printed during extraction, download the review file from CI artifacts and follow the Copilot Chat instructions in `human_reviews/{config-id}/`.