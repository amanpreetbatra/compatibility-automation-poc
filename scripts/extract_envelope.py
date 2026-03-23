#!/usr/bin/env python3
"""Parse parsed docs to extract kernel envelopes (explicit min/max) with evidence.

Conservative rules:
- Only accept bounds when explicitly present on the same line as a support statement.
- Confidence: high when a support phrase and two bounds are on the same line; medium when two bounds
  exist without a clear support phrase; low when ambiguous/missing.
- Never widen based on inference.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml  # type: ignore

PARSED_DIR = Path("docs/parsed")
MANIFEST_FILE = PARSED_DIR / "manifest.json"
AI_ANALYSIS_FILE = PARSED_DIR / "ai_analysis.json"
SOURCES_FILE = Path("docs/sources.yaml")
OUTPUT_RULE = Path("rules/_generated/veritas_802_rhel8.yaml")

SUPPORT_PATTERNS = ["support", "certified", "compatible"]
KERNEL_REGEX = re.compile(r"4\.18\.0-[0-9]+\.el8")


def load_manifest() -> Dict[str, str]:
    if not MANIFEST_FILE.exists():
        return {}
    with MANIFEST_FILE.open() as f:
        return json.load(f)


def read_text(rel_parsed: str) -> List[str]:
    path = PARSED_DIR / rel_parsed
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def find_bounds(lines: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Return min, max, evidence_line, confidence."""
    for line in lines:
        kernels = KERNEL_REGEX.findall(line)
        if len(kernels) >= 2 and any(p in line.lower() for p in SUPPORT_PATTERNS):
            # Use first two kernels on the line, sorted
            k_sorted = sorted(set(kernels))
            return k_sorted[0], k_sorted[-1], line.strip(), "high"

    # Fallback: collect all kernels; if two+ but without support phrase
    all_k = []
    for line in lines:
        all_k.extend(KERNEL_REGEX.findall(line))
    if len(all_k) >= 2:
        k_sorted = sorted(set(all_k))
        return k_sorted[0], k_sorted[-1], "kernels found without explicit support phrase", "medium"

    return None, None, "no explicit bounds found", "low"


def find_unsupported_examples(lines: List[str]) -> List[str]:
    examples: List[str] = []
    for line in lines:
        lowered = line.lower()
        if not any(flag in lowered for flag in ["unsupported", "not supported", "not validated"]):
            continue
        for kernel in KERNEL_REGEX.findall(line):
            if kernel not in examples:
                examples.append(kernel)
    return examples


def load_source_catalog() -> Dict[str, Dict]:
    if not SOURCES_FILE.exists():
        return {}
    with SOURCES_FILE.open() as handle:
        data = yaml.safe_load(handle) or {}
    catalog = {}
    for entry in data.get("sources") or []:
        name = str(entry.get("name", ""))
        if name:
            catalog[name] = entry
    return catalog


def infer_source_type(raw_rel: str, catalog: Dict[str, Dict]) -> str:
    stem = Path(raw_rel).stem
    if stem in catalog:
        return str(catalog[stem].get("type", "vendor_hcl"))
    lowered = raw_rel.lower()
    if "release" in lowered or "_rn" in lowered:
        return "release_notes"
    return "vendor_hcl"


def build_sources(raw_rel: str, catalog: Dict[str, Dict]) -> List[Dict]:
    source_type = infer_source_type(raw_rel, catalog)
    stem = Path(raw_rel).stem
    entry = catalog.get(stem, {})
    source = {
        "name": entry.get("name", raw_rel),
        "reference": raw_rel,
        "type": source_type,
    }
    if entry.get("url"):
        source["url"] = entry["url"]
    return [source]


def load_ai_analysis() -> Dict:
    if not AI_ANALYSIS_FILE.exists():
        return {}
    try:
        return json.loads(AI_ANALYSIS_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def valid_kernel(value: Optional[str]) -> bool:
    return bool(value and KERNEL_REGEX.fullmatch(value))


def build_rule(
    min_k: Optional[str],
    max_k: Optional[str],
    confidence: str,
    sources: List[Dict],
    unsupported_examples: Optional[List[str]] = None,
) -> Dict:
    return {
        "schema_version": 1.1,
        "application": {"name": "veritas_infoscale", "version": "8.0.2"},
        "os": {"family": "rhel", "major_version": 8},
        "kernel": {
            "min": min_k,
            "max": max_k,
            "unsupported_examples": unsupported_examples or [],
        },
        "notes": {
            "risk": "Running outside the certified kernel envelope can destabilize Veritas storage and clustering modules.",
            "remediation": "Keep kernel upgrades within the certified envelope or obtain updated vendor confirmation before rollout.",
        },
        "metadata": {
            "sources": sources,
            "confidence": confidence,
            "owner": "sre-team",
            "last_reviewed": "2026-01-30",
            "review_interval_days": 90,
        },
    }


def main() -> None:
    manifest = load_manifest()
    if not manifest:
        print("No parsed artifacts to scan")
        return

    source_catalog = load_source_catalog()
    ai_analysis = load_ai_analysis()
    ai_status = ai_analysis.get("status")
    ai_available = ai_status == "ok"
    ai_envelope = ai_analysis.get("kernel_envelope") or {}
    ai_min = ai_envelope.get("min")
    ai_max = ai_envelope.get("max")

    min_k = max_k = evidence = None
    confidence = "low"
    source = None
    unsupported_examples: List[str] = []
    analysis_mode = "regex_fallback"
    confidence_rationale = ""
    ambiguity_notes = ""
    ai_sources = []

    if ai_available and valid_kernel(ai_min) and valid_kernel(ai_max):
        min_k = ai_min
        max_k = ai_max
        evidence = {
            "method": "ai_analysis",
            "evidence_min": ai_envelope.get("evidence_min", ""),
            "evidence_max": ai_envelope.get("evidence_max", ""),
        }
        confidence = str(ai_analysis.get("confidence", "low"))
        source_documents = ai_analysis.get("source_documents") or []
        source = source_documents[0]["raw"] if source_documents else "ai_analysis"
        unsupported_examples = [item for item in ai_analysis.get("unsupported_examples") or [] if valid_kernel(item)]
        analysis_mode = "ai"
        confidence_rationale = str(ai_analysis.get("confidence_rationale", "") or "")
        ambiguity_notes = str(ai_analysis.get("ambiguity_notes", "") or "")
        ai_sources = build_sources(source, source_catalog) if source else []
    else:
        ai_available = False
        if ai_status:
            ambiguity_notes = str(ai_analysis.get("error", "") or ai_analysis.get("ambiguity_notes", "") or "")

    if not min_k or not max_k:
        for raw_rel, parsed_rel in manifest.items():
            lines = read_text(parsed_rel)
            if not lines:
                continue
            min_k, max_k, evidence_line, confidence = find_bounds(lines)
            unsupported_examples = find_unsupported_examples(lines)
            source = raw_rel
            evidence = {
                "method": "regex",
                "line": evidence_line,
            }
            if confidence == "high":
                break

    OUTPUT_RULE.parent.mkdir(parents=True, exist_ok=True)
    sources = build_sources(source or "unknown", source_catalog) if source else []

    if not min_k or not max_k:
        print("No explicit envelope extracted; marking as ambiguous")
        rule = build_rule(None, None, "low", sources)
        rule["flags"] = {"ambiguous": True}
        rule["notes"]["evidence"] = evidence
    else:
        rule = build_rule(
            min_k,
            max_k,
            confidence,
            ai_sources or sources,
            unsupported_examples=unsupported_examples,
        )
        rule["notes"]["evidence"] = evidence
        if confidence_rationale:
            rule["notes"]["confidence_rationale"] = confidence_rationale
        if ai_analysis.get("risks"):
            rule["notes"]["ai_risks"] = ai_analysis.get("risks")

    rule.setdefault("flags", {})
    if confidence != "high" or not ai_available:
        rule["flags"]["ambiguous"] = True
    if ambiguity_notes:
        rule["notes"]["ambiguity_notes"] = ambiguity_notes
    rule["metadata"]["analysis_mode"] = analysis_mode
    if ai_status:
        rule["metadata"]["ai_status"] = ai_status
    if ai_analysis.get("model"):
        rule["metadata"]["ai_model"] = ai_analysis.get("model")
    if ai_analysis.get("usage"):
        rule["metadata"]["ai_usage"] = ai_analysis.get("usage")

    with OUTPUT_RULE.open("w") as f:
        yaml.safe_dump(rule, f, sort_keys=False)

    print(f"Wrote generated rule to {OUTPUT_RULE}")


if __name__ == "__main__":
    main()
