Proposal: AI-Assisted Patch Compatibility Decision
Service
Proof of Concept proposal for ServiceNow-integrated patch compatibility validation
1. Executive Summary
This proposal defines a Proof of Concept (POC) to automate the manual compatibility validation step performed before monthly
server patching. Today, for selected servers, engineers ask a System Administrator to confirm whether installed software, such
as Veritas, is compatible with the target RHEL patch level. The proposed solution introduces a ServiceNow-orchestrated
Compatibility Decision API that returns a governed go/no-go/manual-review decision with evidence and audit traceability.
The design keeps ServiceNow as the orchestration engine, introduces a decision engine as a pre-patch gate, and uses AI only
for controlled retrieval and summarization from approved knowledge sources. Deterministic rules, confidence scoring, and
human review thresholds remain the final control points.
2. Problem Statement
Monthly server patching currently includes a manual compatibility validation step for certain software and OS combinations. This
introduces delays, inconsistency in evidence capture, repeated research effort, and dependency on SA availability. The patching
pipeline lacks an automated decision point that can validate whether a target OS patch is safe for a server's installed software
stack before execution.
3. POC Objectives
• Expose an API that ServiceNow can call during the patch workflow.
• Evaluate a server/software/target OS patch combination against approved compatibility data.
• Return structured decisions: compatible, not_compatible, manual_review_required, or unknown.
• Capture evidence, source metadata, decision version, and audit ID.
• Create an exception path for SA review when confidence is low or evidence is missing/conflicting.
4. Business Value
• Reduce manual SA effort for repeatable compatibility checks.
• Improve patch readiness velocity by embedding the check directly in the patch workflow.
• Improve auditability through structured evidence and decision logging.
• Lower operational risk by requiring manual review for uncertain cases.
• Create reusable institutional knowledge from approved compatibility outcomes.
5. Scope
Recommended POC scope is intentionally narrow: RHEL as the OS family, Veritas as the first software/vendor domain, planned
monthly patching, ServiceNow orchestration, one compatibility-check endpoint, curated compatibility KB, and manual review
fallback.
Out of scope: fully autonomous patch approval, unrestricted internet search as a source of truth, multi-vendor expansion,
automated remediation, production patch execution changes without review, and planner-based agentic AI orchestration.
Page 1
AI-Assisted Patch Compatibility Decision Service | Generated 2026-06-16
6. Target Architecture
Operations/Patch Team
        |
        v
ServiceNow Change + Patch Workflow
        |
        | pre-patch compatibility request
        v
API Gateway -> Compatibility Check API
        |              |
        |              +--> Rules Engine
        |              +--> Risk & Confidence Scoring
        |              +--> Audit Event Writer
        |
        +--> Approved Compatibility Knowledge Base
        |       (Vendor matrix, internal KB, SA-approved history)
        |
        +--> AI Retrieval/Summarization Layer
                (approved-source retrieval, evidence summary,
                 conflict detection, guardrail checks)
Decision returned to ServiceNow:
  compatible -> continue patching
  not_compatible -> block/defer patching
  manual_review_required/unknown -> create SA review task
All decisions -> Audit Store -> Splunk/Dynatrace/Monitoring
7. Exact AI Use
AI will be used for decision support only. It will retrieve relevant passages from approved compatibility sources, summarize
evidence, identify conflicts between sources, and generate a human-readable explanation for ServiceNow work notes or SA
review tasks.
AI will not be used to autonomously approve patching, perform unrestricted internet browsing as a source of truth, override
deterministic rules, execute patches, directly modify ServiceNow records outside approved workflow, or suppress manual review
when evidence is incomplete or conflicting.
8. Decision Model
IF exact approved compatibility match exists
  AND source is current
  AND no known exception exists
THEN decision = compatible
IF approved source explicitly marks the combination unsupported
THEN decision = not_compatible
IF source is missing, stale, partial, or conflicting
THEN decision = manual_review_required
IF required input fields are missing
THEN decision = unknown
9. API Contract
Endpoint: POST /api/v1/patch-compatibility/check
Request example:
{
  "change_id": "CHG1234567",
  "correlation_id": "patch-run-2026-07-001",
  "server": {
    "hostname": "server01",
    "environment": "production",
    "business_service": "Payments",
    "os_name": "RHEL",
    "current_os_version": "8.8",
    "target_os_version": "8.10",
Page 2
AI-Assisted Patch Compatibility Decision Service | Generated 2026-06-16
    "current_kernel": "4.18.0-477",
    "target_kernel": "4.18.0-553"
  },
  "software": [{"name": "Veritas InfoScale", "version": "8.0.2"}]
}
Response example:
{
  "audit_id": "compat-20260616-000123",
  "decision": "compatible",
  "confidence": 0.94,
  "risk_level": "low",
  "requires_human_review": false,
  "recommendation": "Proceed with patching during the approved change window.",
  "rule_version": "compat-rules-1.0.0",
  "knowledge_base_version": "veritas-rhel-kb-2026.06"
}
10. ServiceNow Integration
API Decision
ServiceNow Action
compatible
not_compatible
Continue patch workflow and record evidence in work notes.
Block/defer patching and update CR with blocker reason.
manual_review_required
unknown
Create SA review task with evidence summary and audit ID.
Create SA review task and mark compatibility pre-check incomplete.
11. Security, Governance, Observability
• Authenticate ServiceNow/API callers using approved enterprise identity patterns.
• Apply least privilege access to KB, logs, and audit stores.
• Restrict AI retrieval to approved compatibility documents only.
• Validate AI output into a strict schema before returning to workflow.
• Record change ID, request hash, decision, evidence, rule version, KB version, model/prompt version if used, timestamp, and
caller identity.
• Capture metrics: request count, decision distribution, latency, error rate, confidence distribution, manual review rate, and
override rate.
12. POC Success Criteria
• ServiceNow can successfully invoke the API and receive a structured response.
• Known compatible and incompatible test cases are classified correctly.
• Unknown/conflicting cases are routed to SA review.
• 100% of decisions include audit ID and evidence metadata.
• No unsupported combination is automatically marked compatible.
• POC API p95 latency is under 5 seconds for cached KB lookups.
13. Risks and Mitigations
Risk
Mitigation
Incomplete CMDB data
Validate required fields and return unknown/manual review when missing.
Stale vendor documentation
Use source freshness, expiry, KB owner, and approval workflow.
Page 3
AI-Assisted Patch Compatibility Decision Service | Generated 2026-06-16
Risk
AI hallucination
Conflicting evidence
Mitigation
Use AI only for approved-source retrieval/summarization; deterministic rules govern final decision.
Route to SA review and capture conflict details.
API unavailable
Overbroad POC
Fail closed and create manual review task.
Start with Veritas + RHEL only.
14. References
• ARCHDEV-Patch Automation Target Architecture: patch lifecycle includes detection, missing patch identification, CR creation, backup/snapshot,
execution, post-change validation, logging and auditability.
• ARCHDEV-4. Operations Automation Target State Architecture: ServiceNow selected as enterprise orchestration engine; target state includes
decision engine, auto execution, post-change validation, notification, automation code management and CI/CD security controls.
• ARCHDEV-POV - AI Foundational Framework: AI agent/agentic AI definitions, layered enterprise AI architecture, control plane domains including
IAM, guardrails, observability, security/compliance, cost and data management.
Page 4
AI-Assisted Patch Compatibility Decision Service | Generated 2026-06-16

