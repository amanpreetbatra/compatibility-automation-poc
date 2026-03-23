#!/usr/bin/env python3
"""Analyze parsed vendor documentation with GitHub Models and persist JSON output."""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

API_URL = "https://models.github.ai/inference/chat/completions"
ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
PARSED_DIR = Path("docs/parsed")
MANIFEST_FILE = PARSED_DIR / "manifest.json"
PROMPT_FILE = Path("prompts/veritas_rhel8_kernel_analysis.prompt")
OUTPUT_FILE = PARSED_DIR / "ai_analysis.json"
KERNEL_PATTERN = re.compile(r"4\.18\.0-\d+\.el8")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def default_payload(model: str) -> Dict:
    return {
        "status": "error",
        "generated_at": now_iso(),
        "model": model,
        "endpoint": API_URL,
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
        "ambiguity_notes": "",
        "error": "",
    }


def write_result(payload: Dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2))


def load_manifest() -> Dict:
    if not MANIFEST_FILE.exists():
        return {}
    try:
        return json.loads(MANIFEST_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def load_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text().strip()
    return "Analyze the vendor docs and return only JSON."


def collect_documents(manifest: Dict) -> Tuple[List[Dict], str]:
    documents = []
    sections = []
    for raw_rel, parsed_rel in manifest.items():
        parsed_path = PARSED_DIR / parsed_rel
        if not parsed_path.exists():
            continue
        text = parsed_path.read_text(errors="ignore").strip()
        if not text:
            continue
        documents.append({"raw": raw_rel, "parsed": parsed_rel})
        sections.append("FILE: {raw}\n{text}".format(raw=raw_rel, text=text))
    return documents, "\n\n".join(sections)


def extract_content(choice: Dict) -> str:
    message = choice.get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts).strip()
    return str(content).strip()


def parse_json(content: str) -> Dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


def validate_kernel(value: Optional[str], label: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not KERNEL_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid kernel format for {label}: {value!r}")


def normalize_analysis(data: Dict, model: str, documents: List[Dict], usage: Dict) -> Dict:
    envelope = data.get("kernel_envelope") or {}
    unsupported = data.get("unsupported_examples") or []
    risks = data.get("risks") or []

    if not isinstance(unsupported, list):
        raise ValueError("unsupported_examples must be a list")
    if not isinstance(risks, list):
        raise ValueError("risks must be a list")

    validate_kernel(envelope.get("min"), "kernel_envelope.min")
    validate_kernel(envelope.get("max"), "kernel_envelope.max")

    for index, value in enumerate(unsupported):
        validate_kernel(value, f"unsupported_examples[{index}]")

    confidence = str(data.get("confidence", "low")).lower()
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"Invalid confidence value: {confidence!r}")

    ambiguous = bool(data.get("ambiguous", confidence != "high"))

    return {
        "status": "ok",
        "generated_at": now_iso(),
        "model": model,
        "endpoint": API_URL,
        "usage": {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        },
        "source_documents": documents,
        "kernel_envelope": {
            "min": envelope.get("min"),
            "max": envelope.get("max"),
            "evidence_min": str(envelope.get("evidence_min", "") or ""),
            "evidence_max": str(envelope.get("evidence_max", "") or ""),
        },
        "unsupported_examples": [str(item) for item in unsupported],
        "confidence": confidence,
        "confidence_rationale": str(data.get("confidence_rationale", "") or ""),
        "risks": [str(item) for item in risks],
        "ambiguous": ambiguous,
        "ambiguity_notes": str(data.get("ambiguity_notes", "") or ""),
        "error": "",
    }


def build_request(prompt: str, docs_text: str, model: str) -> bytes:
    user_message = (
        "Analyze the following parsed vendor documentation for Veritas InfoScale 8.0.2 on RHEL 8.\n"
        "Return ONLY valid JSON with this exact top-level shape:\n"
        "{"
        '"kernel_envelope":{"min":"4.18.0-193.el8","max":"4.18.0-425.el8","evidence_min":"...","evidence_max":"..."},'
        '"unsupported_examples":["4.18.0-477.el8"],'
        '"confidence":"high|medium|low",'
        '"confidence_rationale":"...",'
        '"risks":["..."],'
        '"ambiguous":false,'
        '"ambiguity_notes":"..."'
        "}\n"
        "Rules:\n"
        "- Use only explicit statements from the supplied text.\n"
        "- Do not infer broader compatibility.\n"
        "- Use empty strings or empty arrays when evidence is missing.\n\n"
        f"{docs_text}"
    )
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
    }
    return json.dumps(payload).encode("utf-8")


def main() -> None:
    load_dotenv(ENV_FILE)
    model = os.environ.get("GITHUB_MODEL", "openai/gpt-4o")
    token = os.environ.get("GITHUB_TOKEN")
    payload = default_payload(model)

    manifest = load_manifest()
    documents, docs_text = collect_documents(manifest)
    payload["source_documents"] = documents

    if not documents or not docs_text:
        payload["status"] = "skipped"
        payload["error"] = "No parsed vendor text found in docs/parsed manifest."
        payload["ambiguity_notes"] = "AI analysis skipped because parsed vendor text was unavailable."
        write_result(payload)
        print(f"No parsed text available; wrote placeholder analysis to {OUTPUT_FILE}")
        return

    if not token:
        payload["status"] = "skipped"
        payload["error"] = (
            "Missing GITHUB_TOKEN. Create a GitHub PAT with models: read scope and export it as GITHUB_TOKEN."
        )
        payload["ambiguity_notes"] = "AI analysis skipped because no GitHub token was provided."
        write_result(payload)
        print(payload["error"])
        print(f"Wrote placeholder analysis to {OUTPUT_FILE}")
        return

    prompt = load_prompt()
    body = build_request(prompt, docs_text, model)
    request = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        payload["status"] = "error"
        payload["error"] = "GitHub Models API returned HTTP {code}: {body}".format(
            code=exc.code,
            body=exc.read().decode("utf-8", errors="ignore"),
        )
        payload["ambiguity_notes"] = "AI analysis failed; regex fallback should be used."
        write_result(payload)
        print(payload["error"])
        return
    except urllib.error.URLError as exc:
        payload["status"] = "error"
        payload["error"] = f"GitHub Models API request failed: {exc.reason}"
        payload["ambiguity_notes"] = "AI analysis failed; regex fallback should be used."
        write_result(payload)
        print(payload["error"])
        return

    try:
        response_json = json.loads(response_body)
        choices = response_json.get("choices") or []
        if not choices:
            raise ValueError("No choices returned by GitHub Models API")
        content = extract_content(choices[0])
        analysis = parse_json(content)
        normalized = normalize_analysis(
            analysis,
            model=model,
            documents=documents,
            usage=response_json.get("usage") or {},
        )
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        payload["status"] = "error"
        payload["error"] = f"Could not parse or validate AI response: {exc}"
        payload["ambiguity_notes"] = "AI analysis response was unusable; regex fallback should be used."
        write_result(payload)
        print(payload["error"])
        return

    write_result(normalized)
    print(f"Wrote AI analysis to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
