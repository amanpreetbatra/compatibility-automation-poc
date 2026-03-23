#!/usr/bin/env python3
"""Run the compatibility automation demo end to end."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, List, Tuple

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
DEMO_DIR = ROOT / "demo" / "sample_vendor_docs"
RAW_DIR = ROOT / "docs" / "raw"
PARSED_DIR = ROOT / "docs" / "parsed"
AI_ANALYSIS_FILE = PARSED_DIR / "ai_analysis.json"
BASELINE_RULE = ROOT / "rules" / "veritas_802_rhel8.yaml"
GENERATED_RULE = ROOT / "rules" / "_generated" / "veritas_802_rhel8.yaml"
DIFF_SUMMARY = PARSED_DIR / "diff_summary.json"
GENERATED_TESTS = ROOT / "tests" / "_generated" / "veritas_802_rhel8_tests.yaml"
DASHBOARD_FILE = ROOT / "dashboard.html"
DEFAULT_MODEL = os.environ.get("GITHUB_MODEL", "openai/gpt-4o")


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def load_yaml(path: Path):
    if not path.exists():
        return {}
    with path.open() as handle:
        return yaml.safe_load(handle) or {}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def log_step(index: int, total: int, title: str) -> None:
    print(f"[{index}/{total}] {title}")


def run_python(script_rel: str) -> None:
    script_path = ROOT / script_rel
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"{script_rel} failed with exit code {completed.returncode}")


def stage_docs() -> List[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    staged = []
    for source in sorted(DEMO_DIR.glob("*")):
        if source.is_dir():
            continue
        destination = RAW_DIR / source.name
        shutil.copy2(source, destination)
        staged.append(destination)
    return staged


def write_ai_placeholder(reason: str, offline: bool) -> None:
    payload = {
        "status": "skipped",
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "model": os.environ.get("GITHUB_MODEL", DEFAULT_MODEL),
        "endpoint": "https://models.github.ai/inference/chat/completions",
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "source_documents": [],
        "kernel_envelope": {
            "min": None,
            "max": None,
            "evidence_min": "",
            "evidence_max": "",
        },
        "unsupported_examples": [],
        "confidence": "low",
        "confidence_rationale": "",
        "risks": [],
        "ambiguous": True,
        "ambiguity_notes": reason,
        "error": reason,
        "mode": "offline" if offline else "skipped",
    }
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    AI_ANALYSIS_FILE.write_text(json.dumps(payload, indent=2))


def format_tokens(usage: Dict) -> str:
    total = usage.get("total_tokens")
    if total in {None, 0, "0"}:
        return "n/a"
    return (
        f"{usage.get('prompt_tokens', 0)} prompt / "
        f"{usage.get('completion_tokens', 0)} completion / "
        f"{usage.get('total_tokens', 0)} total"
    )


def build_evidence_text(rule: Dict) -> str:
    evidence = rule.get("notes", {}).get("evidence")
    if isinstance(evidence, dict):
        if evidence.get("method") == "ai_analysis":
            min_line = evidence.get("evidence_min", "")
            max_line = evidence.get("evidence_max", "")
            return f"Minimum bound evidence:\n{min_line}\n\nMaximum bound evidence:\n{max_line}".strip()
        return str(evidence.get("line", ""))
    if isinstance(evidence, str):
        return evidence
    return "No evidence captured."


def build_verdict(summary_entry: Dict) -> Tuple[str, str, str]:
    decision = summary_entry.get("decision", "pr_block_auto_merge")
    if decision == "info":
        return "COMPATIBLE — NO CHANGE", "#1fc16b", "#163922"
    return "REVIEW REQUIRED", "#ff6f6f", "#4a1f1f"


def render_test_rows(tests: List[Dict]) -> str:
    rows = []
    for test in tests:
        expected = test.get("expected", {})
        decision = expected.get("decision", "NO_GO")
        badge = "badge-go" if decision == "GO" else "badge-no-go"
        rows.append(
            "<tr>"
            f"<td>{escape(str(test.get('id', 'n/a')))}</td>"
            f"<td><code>{escape(str(test.get('target_kernel', 'n/a')))}</code></td>"
            f"<td><span class=\"badge {badge}\">{escape(str(decision))}</span></td>"
            f"<td>{escape(str(test.get('rationale', '')))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def generate_dashboard(offline: bool) -> None:
    baseline = load_yaml(BASELINE_RULE)
    generated = load_yaml(GENERATED_RULE)
    diff_summary = load_json(DIFF_SUMMARY)
    ai_analysis = load_json(AI_ANALYSIS_FILE)
    tests = load_yaml(GENERATED_TESTS)
    if not isinstance(tests, list):
        tests = []

    summary_entry = diff_summary.get(str(Path("rules/_generated/veritas_802_rhel8.yaml")), {})
    verdict_text, verdict_color, verdict_bg = build_verdict(summary_entry)
    metadata = generated.get("metadata", {})
    notes = generated.get("notes", {})
    ai_usage = ai_analysis.get("usage", {})
    confidence = metadata.get("confidence", ai_analysis.get("confidence", "low"))
    ambiguous = generated.get("flags", {}).get("ambiguous", True)
    evidence_text = build_evidence_text(generated)
    risks = ai_analysis.get("risks") or notes.get("ai_risks") or []
    if not isinstance(risks, list):
        risks = [str(risks)]

    ai_section = ""
    if not offline:
        ai_section = f"""
        <section class="panel">
          <h2>AI Analysis</h2>
          <div class="meta-grid">
            <div><span class="meta-label">Model</span><strong>{escape(str(ai_analysis.get('model', DEFAULT_MODEL)))}</strong></div>
            <div><span class="meta-label">Tokens</span><strong>{escape(format_tokens(ai_usage))}</strong></div>
            <div><span class="meta-label">Confidence</span><strong>{escape(str(ai_analysis.get('confidence', confidence)))}</strong></div>
            <div><span class="meta-label">Ambiguous</span><strong>{escape(str(ai_analysis.get('ambiguous', ambiguous)))}</strong></div>
          </div>
          <p class="body-copy">{escape(str(ai_analysis.get('confidence_rationale', 'No AI rationale captured.')))}</p>
          <div class="risk-box">
            <h3>Risks</h3>
            <ul>
              {''.join(f'<li>{escape(str(item))}</li>' for item in risks) or '<li>No AI risks captured.</li>'}
            </ul>
          </div>
        </section>
        """

    offline_banner = ""
    if offline:
        offline_banner = """
        <div class="offline-banner">
          Offline demo mode is active. This run used regex extraction only and intentionally marked the result ambiguous for manual review because AI analysis was skipped.
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compatibility Automation Demo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0f0f12;
      --panel: #17181d;
      --panel-strong: #1d1f26;
      --border: rgba(255, 255, 255, 0.08);
      --text: #f4f5f7;
      --muted: #a4a9b6;
      --accent: #4ecdc4;
      --danger: #ff6f6f;
      --success: #1fc16b;
      --warning: #f3bc55;
      --code-bg: #121318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Plus Jakarta Sans", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(78, 205, 196, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(255, 111, 111, 0.14), transparent 24%),
        linear-gradient(180deg, #121319 0%, #0f0f12 60%, #0c0c0f 100%);
    }}
    .shell {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 24px 56px;
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-size: 12px;
      margin-bottom: 14px;
      display: block;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 1.04;
    }}
    .subhead {{
      color: var(--muted);
      max-width: 760px;
      line-height: 1.6;
      margin-bottom: 28px;
    }}
    .verdict-card {{
      background: linear-gradient(135deg, {verdict_bg}, rgba(255,255,255,0.03));
      border: 1px solid {verdict_color};
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
      margin-bottom: 22px;
    }}
    .verdict-label {{
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: {verdict_color};
      margin-bottom: 12px;
      display: block;
    }}
    .verdict-title {{
      font-size: clamp(1.8rem, 3vw, 2.8rem);
      margin: 0 0 8px;
    }}
    .panel-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
      margin: 22px 0;
    }}
    .panel {{
      background: rgba(23, 24, 29, 0.88);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      backdrop-filter: blur(10px);
    }}
    .panel h2, .panel h3 {{
      margin-top: 0;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .meta-label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .kernel-compare {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .kernel-box {{
      background: var(--panel-strong);
      border-radius: 16px;
      padding: 18px;
      border: 1px solid var(--border);
    }}
    code, pre {{
      font-family: "JetBrains Mono", monospace;
    }}
    code {{
      background: var(--code-bg);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 8px;
      padding: 2px 6px;
    }}
    pre {{
      background: var(--code-bg);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 16px;
      padding: 18px;
      overflow-x: auto;
      white-space: pre-wrap;
      line-height: 1.6;
      color: #dfe4ea;
    }}
    .body-copy {{
      color: var(--muted);
      line-height: 1.7;
    }}
    .offline-banner {{
      background: rgba(243, 188, 85, 0.12);
      border: 1px solid rgba(243, 188, 85, 0.4);
      color: #f9d27b;
      border-radius: 18px;
      padding: 16px 18px;
      margin-bottom: 20px;
    }}
    .risk-box {{
      margin-top: 18px;
      background: rgba(255,255,255,0.03);
      border-radius: 16px;
      padding: 16px 18px;
    }}
    .risk-box ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 14px 12px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 6px 10px;
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .badge-go {{
      background: rgba(31, 193, 107, 0.14);
      color: #79e3a9;
    }}
    .badge-no-go {{
      background: rgba(255, 111, 111, 0.14);
      color: #ff9f9f;
    }}
    .steps {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .step {{
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 16px;
      padding: 16px;
    }}
    .step strong {{
      display: block;
      margin-bottom: 8px;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 14px;
      text-align: center;
    }}
    @media (max-width: 820px) {{
      .panel-grid, .kernel-compare {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <span class="eyebrow">Compatibility Automation PoC</span>
    <h1>RHEL 8 patch compatibility check for Veritas InfoScale 8.0.2</h1>
    <p class="subhead">This dashboard captures the end-to-end demo pipeline: vendor document staging, deterministic extraction, optional GitHub Models analysis, rule generation, safety diffing, and generated GO/NO_GO patch test cases.</p>
    {offline_banner}
    <section class="verdict-card">
      <span class="verdict-label">Current verdict</span>
      <h2 class="verdict-title">{escape(verdict_text)}</h2>
      <p class="body-copy">Gate decision: <strong>{escape(str(summary_entry.get('decision', 'pr_block_auto_merge')))}</strong> because <strong>{escape(str(summary_entry.get('reason', 'ambiguous')))}</strong>.</p>
    </section>

    <div class="panel-grid">
      <section class="panel">
        <h2>Kernel Envelope Comparison</h2>
        <div class="kernel-compare">
          <div class="kernel-box">
            <span class="meta-label">Baseline Rule</span>
            <p>Minimum: <code>{escape(str(baseline.get('kernel', {}).get('min', 'n/a')))}</code></p>
            <p>Maximum: <code>{escape(str(baseline.get('kernel', {}).get('max', 'n/a')))}</code></p>
          </div>
          <div class="kernel-box">
            <span class="meta-label">Extracted Rule</span>
            <p>Minimum: <code>{escape(str(generated.get('kernel', {}).get('min', 'n/a')))}</code></p>
            <p>Maximum: <code>{escape(str(generated.get('kernel', {}).get('max', 'n/a')))}</code></p>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2>Pipeline Metadata</h2>
        <div class="meta-grid">
          <div><span class="meta-label">Application</span><strong>veritas_infoscale 8.0.2</strong></div>
          <div><span class="meta-label">OS</span><strong>RHEL 8</strong></div>
          <div><span class="meta-label">Analysis Mode</span><strong>{escape(str(metadata.get('analysis_mode', 'regex_fallback')))}</strong></div>
          <div><span class="meta-label">Gate</span><strong>{escape(str(summary_entry.get('decision', 'pr_block_auto_merge')))}</strong></div>
          <div><span class="meta-label">Confidence</span><strong>{escape(str(confidence))}</strong></div>
          <div><span class="meta-label">Ambiguous</span><strong>{escape(str(ambiguous))}</strong></div>
        </div>
      </section>
    </div>

    {ai_section}

    <section class="panel">
      <h2>Evidence</h2>
      <p class="body-copy">Exact vendor text used to support the extracted bounds.</p>
      <pre>{escape(evidence_text)}</pre>
    </section>

    <section class="panel">
      <h2>Generated Test Cases</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Target Kernel</th>
            <th>Decision</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {render_test_rows(tests)}
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h2>How This Pipeline Works</h2>
      <div class="steps">
        <div class="step"><strong>1. Stage docs</strong>Sample vendor documents are copied into <code>docs/raw/</code>.</div>
        <div class="step"><strong>2. Detect changes</strong>SHA-256 hashing identifies document deltas and records a pending queue.</div>
        <div class="step"><strong>3. Extract text</strong>Plain text is preserved as-is and non-text formats are stubbed with provenance.</div>
        <div class="step"><strong>4. AI analysis</strong>GitHub Models optionally extracts envelope evidence and risk statements into JSON.</div>
        <div class="step"><strong>5. Extract envelope</strong>AI output is validated against the kernel regex, then regex fallback runs if needed.</div>
        <div class="step"><strong>6. Diff rules</strong>The generated rule is compared with the baseline to classify change safety.</div>
        <div class="step"><strong>7. Generate tests</strong>GO and NO_GO kernel cases are emitted for the compatibility engine.</div>
        <div class="step"><strong>8. Dashboard</strong>A dark-theme audit view summarizes verdict, evidence, metadata, and tests.</div>
      </div>
    </section>

    <footer>
      Generated {escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}. Audit note: AI never auto-approves a widened or ambiguous compatibility envelope.
    </footer>
  </div>
</body>
</html>
"""
    DASHBOARD_FILE.write_text(html)


def print_artifacts() -> None:
    artifacts = [
        GENERATED_RULE,
        GENERATED_TESTS,
        DIFF_SUMMARY,
        AI_ANALYSIS_FILE,
        DASHBOARD_FILE,
    ]
    print("\nArtifacts")
    for artifact in artifacts:
        print(f"- {artifact.relative_to(ROOT)}")


def main() -> None:
    load_dotenv(ENV_FILE)
    parser = argparse.ArgumentParser(description="Run the compatibility automation demo.")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip GitHub Models analysis and run in regex-only mode.",
    )
    args = parser.parse_args()
    model = os.environ.get("GITHUB_MODEL", DEFAULT_MODEL)

    total_steps = 8
    log_step(1, total_steps, "Stage docs")
    staged = stage_docs()
    print(f"Staged {len(staged)} file(s) from demo/sample_vendor_docs into docs/raw")

    log_step(2, total_steps, "Detect changes")
    run_python("scripts/detect_changes.py")

    log_step(3, total_steps, "Extract text")
    run_python("scripts/extract_text.py")

    log_step(4, total_steps, "AI analysis")
    if args.offline:
        write_ai_placeholder("Offline mode requested; AI analysis was skipped.", offline=True)
        print("Offline mode enabled; wrote skipped AI analysis placeholder.")
    elif not os.environ.get("GITHUB_TOKEN"):
        write_ai_placeholder("No GITHUB_TOKEN found; AI analysis was skipped.", offline=False)
        print("No GITHUB_TOKEN found; wrote skipped AI analysis placeholder.")
    else:
        run_python("scripts/analyze_with_ai.py")

    log_step(5, total_steps, "Extract envelope")
    run_python("scripts/extract_envelope.py")

    log_step(6, total_steps, "Diff rules")
    run_python("scripts/diff_rules.py")

    log_step(7, total_steps, "Generate tests")
    run_python("scripts/generate_tests.py")

    log_step(8, total_steps, "Generate HTML dashboard")
    generate_dashboard(offline=args.offline or not os.environ.get("GITHUB_TOKEN"))
    print(f"Wrote dashboard to {DASHBOARD_FILE.relative_to(ROOT)}")
    print(f"Model setting: {model}")

    print_artifacts()


if __name__ == "__main__":
    main()
