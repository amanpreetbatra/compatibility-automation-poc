# Compatibility Checker — Copilot PoC

Ask VS Code Copilot whether a kernel version is safe to patch to, and get a structured answer with references.

---

## The Problem

Before patching a Linux system, you need to verify that the new kernel version is compatible with your installed applications (Veritas InfoScale, Oracle DB, SAP HANA, etc.). This means:

- Searching vendor HCL pages
- Reading release notes
- Checking Red Hat advisories
- Cross-referencing multiple docs

This takes 30–60 minutes per patch window. It's manual, error-prone, and undocumented.

---

## The Solution (This PoC)

**Ask Copilot. Get an answer in seconds.**

Open VS Code Copilot Chat and type:

```
Is Veritas InfoScale 8.0.2 compatible with RHEL 8 kernel 4.18.0-477.el8?
```

Copilot searches the vendor HCL pages, release notes, and the internet — guided by the sources defined in this repo — and returns:

```
### Verdict: ❌ NOT COMPATIBLE

Reason: Supported range is 4.18.0-193.el8 to 4.18.0-425.el8.
        Kernel 4.18.0-477.el8 exceeds the upper bound.

References:
  1. Veritas HCL (Oct 2023) — https://veritas.com/... — Section: Supported Kernels RHEL 8
  2. Veritas 8.0.2 Release Notes — https://veritas.com/...

Confidence: High
Note: Do not patch. Highest safe kernel is 4.18.0-425.el8.
```

---

## How It Works

```
You ask Copilot
      │
      ▼
copilot-instructions.md        ← tells Copilot exactly how to answer
      │
      ▼
sources/{app}.yaml             ← per-app list of HCL URLs, release notes, search terms
      │
      ▼
Copilot searches those URLs + internet
      │
      ▼
Returns: YES/NO + Reason + References + Confidence
```

---

## Asking a Question

Open **Copilot Chat** in VS Code (`Ctrl+Shift+I` / `Cmd+Shift+I`) and ask naturally:

```
Is Veritas InfoScale 8.0.2 compatible with RHEL 8 kernel 4.18.0-305.el8?
```

```
Can I patch my RHEL 8 system to kernel 4.18.0-477.el8 if I have Veritas InfoScale 8.0.2?
```

```
What is the highest kernel I can safely use with Veritas InfoScale 8.0.2 on RHEL 8?
```

```
Is Oracle DB 19c certified on RHEL 8 kernel 4.18.0-425.el8?
```

---

## Adding a New Application

Create `sources/{app-name}.yaml`:

```yaml
app: your-app
description: Your Application Name
vendor: Vendor Name

versions:
  - "1.0"
  - "2.0"

platforms:
  - rhel
  - ubuntu

docs:
  - name: Official HCL
    url: https://vendor.com/hcl
    type: hcl
    notes: Primary source for compatibility

  - name: Release Notes
    url: https://vendor.com/release-notes
    type: release_notes

search_terms:
  - "your-app {version} {platform} kernel compatibility"
  - "site:vendor.com your-app {version} supported kernels"
```

That's it. Copilot will automatically use these sources next time you ask about that app.

---

## Supported Applications

| App | Versions | Source File |
|-----|---------|------------|
| Veritas InfoScale | 7.4, 8.0, 8.0.2, 9.0, 9.1 | `sources/veritas-infoscale.yaml` |
| Oracle Database | 19c, 21c, 23ai | `sources/oracle-db.yaml` |
| SAP HANA | 2.0 SPS06–08 | `sources/sap-hana.yaml` |

---

## Future: LLM API Integration

When an LLM API key is approved, the same question can be answered automatically — no Copilot needed. The `sources/` structure and answer format stay exactly the same; only the backend changes.

```python
# Future: one environment variable switches from Copilot to API
LLM_PROVIDER=openai   # or anthropic, azure
LLM_API_KEY=sk-...
```

---

## Repository Structure

```
.github/
  copilot-instructions.md   ← Copilot behaviour definition (the core of this PoC)
sources/
  veritas-infoscale.yaml    ← Veritas HCL URLs + search terms
  oracle-db.yaml            ← Oracle certification matrix URLs
  sap-hana.yaml             ← SAP HANA support notes URLs
docs/
  architecture_guide.pdf    ← Architecture document
  presentation.pptx         ← Slide deck for stakeholders
README.md
```
