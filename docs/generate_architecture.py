#!/usr/bin/env python3
"""Generate the architecture PDF for the Compatibility Checker PoC."""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import Flowable

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#0f2044")
BLUE       = colors.HexColor("#1d4ed8")
BLUE_LIGHT = colors.HexColor("#dbeafe")
BLUE_PALE  = colors.HexColor("#eff6ff")
GREEN      = colors.HexColor("#16a34a")
GREEN_PALE = colors.HexColor("#dcfce7")
RED        = colors.HexColor("#dc2626")
RED_PALE   = colors.HexColor("#fee2e2")
AMBER      = colors.HexColor("#d97706")
AMBER_PALE = colors.HexColor("#fef3c7")
GREY       = colors.HexColor("#6b7280")
GREY_LIGHT = colors.HexColor("#f3f4f6")
GREY_RULE  = colors.HexColor("#e5e7eb")
WHITE      = colors.white

W, H = A4
MARGIN = 20 * mm
CW = W - 2 * MARGIN


# ── Cover ─────────────────────────────────────────────────────────────────────
class Cover(Flowable):
    def __init__(self): super().__init__(); self.width = W; self.height = H
    def draw(self):
        c = self.canv
        c.setFillColor(NAVY); c.rect(0, 0, W, H, fill=1, stroke=0)
        # accent shapes
        c.setFillColor(colors.HexColor("#162a55"))
        c.circle(W * 0.88, H * 0.78, 85, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#1a3260"))
        c.circle(W * 0.08, H * 0.12, 55, fill=1, stroke=0)
        c.setFillColor(BLUE); c.rect(0, H * 0.44, W, 2.5, fill=1, stroke=0)

        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(W/2, H * 0.65, "Compatibility Checker")
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(W/2, H * 0.65 - 42, "Copilot PoC")
        c.setFillColor(colors.HexColor("#93c5fd")); c.setFont("Helvetica", 12)
        c.drawCentredString(W/2, H * 0.65 - 68, "Architecture & Design Document")

        c.setStrokeColor(BLUE); c.setLineWidth(1)
        c.line(W*0.28, H*0.44-18, W*0.72, H*0.44-18)

        c.setFillColor(colors.HexColor("#93c5fd")); c.setFont("Helvetica", 9)
        c.drawCentredString(W/2, H*0.44-36, "Ask · Search · Know  —  Before Every Patch")

        c.setFillColor(colors.HexColor("#1e3a6e"))
        c.rect(0, 0, W, 20*mm, fill=1, stroke=0)
        c.setFillColor(GREY); c.setFont("Helvetica", 8)
        c.drawCentredString(W/2, 8*mm, "Infrastructure Reliability  ·  2026")


# ── Simple arrow-connected flow diagram ──────────────────────────────────────
class FlowDiagram(Flowable):
    def __init__(self, steps, width, bh=18*mm):
        super().__init__()
        self.steps = steps; self.width = width; self.bh = bh
        self.height = bh + 8*mm

    def draw(self):
        c = self.canv; n = len(self.steps)
        aw = 7*mm; bw = (self.width - aw*(n-1)) / n; y0 = 3*mm
        for i, (lbl, sub, col) in enumerate(self.steps):
            x = i*(bw+aw)
            c.setFillColor(col); c.setStrokeColor(NAVY); c.setLineWidth(0.5)
            c.roundRect(x, y0, bw, self.bh, 3, fill=1, stroke=1)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x+bw/2, y0+self.bh/2+2, lbl)
            if sub:
                c.setFont("Helvetica", 5.5)
                c.drawCentredString(x+bw/2, y0+self.bh/2-6, sub)
            if i < n-1:
                ax = x+bw; ay = y0+self.bh/2
                c.setStrokeColor(BLUE); c.setFillColor(BLUE); c.setLineWidth(1.2)
                c.line(ax, ay, ax+aw-2, ay)
                p = c.beginPath(); tip = ax+aw-1
                p.moveTo(tip, ay); p.lineTo(tip-3, ay+2); p.lineTo(tip-3, ay-2)
                p.close(); c.drawPath(p, fill=1, stroke=0)


# ── Verdict box ───────────────────────────────────────────────────────────────
class VerdictBox(Flowable):
    def __init__(self, width):
        super().__init__(); self.width = width; self.height = 80*mm

    def draw(self):
        c = self.canv; W = self.width; bw = W/3 - 3*mm
        boxes = [
            ("✅ COMPATIBLE",     "Found in vendor HCL\nwith exact version range",    GREEN,  GREEN_PALE),
            ("❌ NOT COMPATIBLE", "Kernel outside\ncertified envelope",               RED,    RED_PALE),
            ("⚠️ UNKNOWN",        "Could not find\ndefinitive source",               AMBER,  AMBER_PALE),
        ]
        for i, (title, sub, accent, bg) in enumerate(boxes):
            x = i*(bw+4.5*mm); bh = 64*mm
            c.setFillColor(bg); c.setStrokeColor(accent); c.setLineWidth(1.5)
            c.roundRect(x, 0, bw, bh, 5, fill=1, stroke=1)
            c.setFillColor(accent)
            c.roundRect(x, bh-16*mm, bw, 16*mm, 5, fill=1, stroke=0)
            c.rect(x, bh-16*mm, bw, 8*mm, fill=1, stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x+bw/2, bh-9*mm, title)
            c.setFillColor(NAVY); c.setFont("Helvetica", 7)
            for li, line in enumerate(sub.split("\n")):
                c.drawCentredString(x+bw/2, bh-20*mm-li*9, line)

            # what you get
            items = ["Verdict", "Reason", "References", "Confidence", "Patch note"]
            c.setFont("Helvetica-Bold", 6.5); c.setFillColor(GREY)
            c.drawString(x+4*mm, 35*mm, "Answer includes:")
            c.setFont("Helvetica", 6.5); c.setFillColor(NAVY)
            for j, item in enumerate(items):
                c.drawString(x+5*mm, 29*mm-j*7, f"• {item}")


# ── Sources structure diagram ─────────────────────────────────────────────────
class SourcesDiagram(Flowable):
    def __init__(self, width):
        super().__init__(); self.width = width; self.height = 72*mm

    def draw(self):
        c = self.canv; W = self.width
        # central "sources/" folder
        cx = W/2; cy = self.height/2
        c.setFillColor(BLUE); c.setStrokeColor(NAVY); c.setLineWidth(0.5)
        c.roundRect(cx-22*mm, cy-8*mm, 44*mm, 16*mm, 4, fill=1, stroke=1)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, cy+1, "sources/")
        c.setFont("Helvetica", 6); c.drawCentredString(cx, cy-6, "per-app YAML files")

        apps = [
            ("veritas-infoscale.yaml", 0.12, 0.82),
            ("oracle-db.yaml",         0.12, 0.50),
            ("sap-hana.yaml",          0.12, 0.18),
            ("your-app.yaml",          0.88, 0.50),
        ]
        cols = [BLUE, colors.HexColor("#0891b2"), colors.HexColor("#7c3aed"), GREY]
        for (name, fx, fy), col in zip(apps, cols):
            bx = fx*W - 20*mm; by = fy*self.height - 6*mm
            c.setFillColor(colors.HexColor("#f0f9ff")); c.setStrokeColor(col)
            c.setLineWidth(1); c.roundRect(bx, by, 40*mm, 12*mm, 3, fill=1, stroke=1)
            c.setFillColor(NAVY); c.setFont("Courier", 6.5)
            c.drawCentredString(bx+20*mm, by+4, name)
            # line to center
            c.setStrokeColor(col); c.setLineWidth(0.8)
            lx = cx if fx < 0.5 else cx-22*mm if fx < 0.5 else cx+22*mm
            ex = bx+40*mm if fx < 0.5 else bx
            c.line(ex, by+6*mm, lx, cy)

        # right side: what each YAML contains
        labels = ["vendor docs", "HCL URLs", "release note URLs", "search terms"]
        c.setFont("Helvetica", 6.5); c.setFillColor(GREY)
        for i, lbl in enumerate(labels):
            c.drawString(W*0.66, self.height*0.72-i*8, f"• {lbl}")
        c.setFont("Helvetica-Bold", 7); c.setFillColor(NAVY)
        c.drawString(W*0.66, self.height*0.78, "Each file contains:")


# ── Helpers ───────────────────────────────────────────────────────────────────
def S():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", fontSize=22, textColor=NAVY, fontName="Helvetica-Bold",
                             leading=28, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontSize=13, textColor=NAVY, fontName="Helvetica-Bold",
                             leading=18, spaceBefore=8, spaceAfter=3),
        "h3": ParagraphStyle("h3", fontSize=10, textColor=BLUE, fontName="Helvetica-Bold",
                             leading=14, spaceBefore=5, spaceAfter=2),
        "body": ParagraphStyle("body", fontSize=9, textColor=colors.black,
                               fontName="Helvetica", leading=14, spaceAfter=3),
        "code": ParagraphStyle("code", fontSize=8, textColor=NAVY, fontName="Courier",
                               backColor=GREY_LIGHT, leftIndent=8, rightIndent=8,
                               leading=12, spaceBefore=3, spaceAfter=3, borderPad=4),
        "caption": ParagraphStyle("caption", fontSize=7.5, textColor=GREY,
                                  fontName="Helvetica-Oblique", alignment=1,
                                  spaceBefore=2, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", fontSize=9, textColor=colors.black,
                                 fontName="Helvetica", leading=13, leftIndent=10, spaceAfter=2),
    }

def sp(h=4): return Spacer(1, h*mm)
def hr(): return HRFlowable(width="100%", thickness=0.5, color=GREY_RULE, spaceAfter=4)


def on_page(canvas, doc):
    if doc.page == 1: return
    canvas.saveState()
    canvas.setFillColor(NAVY); canvas.rect(0, H-11*mm, W, 11*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, H-7*mm, "Compatibility Checker — Architecture Guide")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W-MARGIN, H-7*mm, f"Page {doc.page}")
    canvas.setFillColor(GREY_LIGHT); canvas.rect(0, 0, W, 7*mm, fill=1, stroke=0)
    canvas.setFillColor(GREY); canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W/2, 2.5*mm, "Internal Use")
    canvas.restoreState()

def on_first(canvas, doc):
    canvas.saveState()
    cover = Cover(); cover.canv = canvas; cover.draw()
    canvas.restoreState()

def on_any(canvas, doc):
    if doc.page == 1: on_first(canvas, doc)
    else: on_page(canvas, doc)


# ── Build ─────────────────────────────────────────────────────────────────────
def build(out: Path):
    s = S()
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=16*mm, bottomMargin=13*mm,
                            title="Compatibility Checker — Architecture Guide")
    story = [Spacer(1, H - 2*MARGIN), PageBreak()]

    # ── 1. Overview ────────────────────────────────────────────────────────────
    story += [
        Paragraph("1. Overview", s["h1"]), hr(), sp(2),
        Paragraph(
            "Before patching a Linux system, engineers must manually verify that the target "
            "kernel version is certified for every installed enterprise application. This involves "
            "searching vendor HCL pages, reading release notes, and cross-checking advisories — "
            "a process that takes 30–60 minutes per patch window and is prone to human error.",
            s["body"]),
        sp(1),
        Paragraph(
            "This PoC eliminates that manual step. An engineer asks a plain-English question "
            "in VS Code Copilot Chat and receives a structured answer — verdict, reason, "
            "references — in seconds. The system uses per-application source files to guide "
            "Copilot to the right vendor documents, and is designed to plug in an LLM API "
            "in the future with zero structural changes.",
            s["body"]),
        sp(3),
    ]

    prob_data = [
        ["Before (Manual)", "After (This PoC)"],
        ["Open browser, navigate to vendor HCL page", "Ask one question in Copilot Chat"],
        ["Search release notes for kernel version", "Get answer in < 30 seconds"],
        ["Cross-check with Red Hat advisories",       "Receive references to validate"],
        ["Document findings in a spreadsheet",        "Answer is structured and repeatable"],
        ["30–60 min per patch window",                "< 1 min per patch window"],
    ]
    pt = Table(prob_data, colWidths=[CW/2, CW/2])
    pt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("BOX",           (0,0),(-1,-1), 0.5, GREY_RULE),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, GREY_RULE),
    ]))
    story += [pt, PageBreak()]

    # ── 2. How It Works ────────────────────────────────────────────────────────
    story += [Paragraph("2. How It Works", s["h1"]), hr(), sp(2)]
    flow_steps = [
        ("User asks\nCopilot",      "plain English",        BLUE),
        ("copilot-\ninstructions",  "behaviour rules",      colors.HexColor("#7c3aed")),
        ("sources/\n{app}.yaml",    "vendor URLs",          colors.HexColor("#0891b2")),
        ("Search\n& Fetch",         "HCL + internet",       GREEN),
        ("Structured\nAnswer",      "verdict + refs",       colors.HexColor("#d97706")),
    ]
    story += [
        FlowDiagram(flow_steps, CW),
        Paragraph("Figure 1 — End-to-end flow", s["caption"]),
        sp(4),
        Paragraph("Step-by-step", s["h2"]),
    ]
    steps = [
        ("Ask", "Engineer types a plain-English question into VS Code Copilot Chat:\n"
                '"Is Veritas InfoScale 8.0.2 compatible with RHEL 8 kernel 4.18.0-477.el8?"'),
        ("Instructions", "Copilot reads .github/copilot-instructions.md, which tells it exactly "
                         "how to answer compatibility questions — format, confidence levels, "
                         "citation style, and when to say UNKNOWN."),
        ("Sources", "Copilot reads sources/veritas-infoscale.yaml, which lists the official "
                    "vendor HCL URL, release notes URL, and recommended search terms for that app."),
        ("Search", "Copilot fetches those URLs and searches the internet using the configured "
                   "search terms, looking for the certified kernel version range."),
        ("Answer", "Copilot returns a structured answer: COMPATIBLE / NOT COMPATIBLE / UNKNOWN, "
                   "the reason, specific version bounds, reference URLs, and a patching note."),
    ]
    for num, (title, detail) in enumerate(steps, 1):
        story.append(KeepTogether([
            Table([[
                Paragraph(f"<b>{num}</b>", ParagraphStyle("n", fontSize=9, textColor=WHITE,
                          fontName="Helvetica-Bold", alignment=1)),
                Paragraph(f"<b>{title}</b> — {detail}", s["body"]),
            ]], colWidths=[8*mm, CW-8*mm], style=TableStyle([
                ("BACKGROUND", (0,0),(0,0), BLUE),
                ("VALIGN",     (0,0),(-1,-1), "TOP"),
                ("TOPPADDING", (0,0),(-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LEFTPADDING", (0,0),(-1,-1), 4),
            ])),
            sp(1.5),
        ]))
    story.append(PageBreak())

    # ── 3. Verdict Format ──────────────────────────────────────────────────────
    story += [Paragraph("3. Answer Format", s["h1"]), hr(), sp(2),
              Paragraph("Every answer follows the same structure regardless of the verdict:", s["body"]),
              sp(3), VerdictBox(CW),
              Paragraph("Figure 2 — Three possible verdicts and what each answer contains", s["caption"]),
              sp(4)]

    story += [Paragraph("Example answer", s["h2"]),
              Paragraph(
                  "## Compatibility Check\n\n"
                  "Application: Veritas InfoScale 8.0.2\n"
                  "Platform:    RHEL 8\n"
                  "Kernel:      4.18.0-477.el8\n\n"
                  "### Verdict: NOT COMPATIBLE\n\n"
                  "Reason: Supported range is 4.18.0-193.el8 to 4.18.0-425.el8.\n"
                  "Kernel 4.18.0-477.el8 exceeds the upper bound.\n\n"
                  "References:\n"
                  "1. Veritas HCL Oct 2023 — https://veritas.com/... — Section: Supported Kernels RHEL 8\n"
                  "2. Release Notes 8.0.2  — https://veritas.com/... — Known Limitations\n\n"
                  "Confidence: High\n"
                  "Note: Safe maximum is 4.18.0-425.el8. Do not patch beyond this.",
                  s["code"]),
              PageBreak()]

    # ── 4. Sources Structure ───────────────────────────────────────────────────
    story += [Paragraph("4. Sources Structure", s["h1"]), hr(), sp(2),
              Paragraph(
                  "Each application has its own YAML file in <font face='Courier'>sources/</font>. "
                  "These files tell Copilot exactly where to look — vendor HCL pages, release notes, "
                  "support portals — and what search terms to use. Adding a new application takes "
                  "less than 5 minutes.",
                  s["body"]),
              sp(3), SourcesDiagram(CW),
              Paragraph("Figure 3 — Per-application source files", s["caption"]),
              sp(4)]

    story += [Paragraph("Source file structure", s["h2"]),
              Paragraph(
                  "app: veritas-infoscale\n"
                  "vendor: Veritas Technologies\n"
                  "versions: [8.0.2, 9.1]\n"
                  "platforms: [rhel, ubuntu, sles]\n\n"
                  "docs:\n"
                  "  - name: Veritas InfoScale HCL\n"
                  "    url: https://www.veritas.com/support/en_US/article/000127013\n"
                  "    type: hcl\n"
                  "    notes: Primary source — lists supported OS, kernel, hardware\n\n"
                  "  - name: Release Notes\n"
                  "    url: https://www.veritas.com/support/en_US/article/000127005\n"
                  "    type: release_notes\n\n"
                  "search_terms:\n"
                  "  - \"veritas infoscale {version} rhel {platform_version} kernel compatibility\"\n"
                  "  - \"site:veritas.com infoscale {version} supported kernels\"",
                  s["code"]),
              PageBreak()]

    # ── 5. Future LLM Integration ──────────────────────────────────────────────
    story += [Paragraph("5. Future: LLM API Integration", s["h1"]), hr(), sp(2),
              Paragraph(
                  "The PoC is designed so that switching from Copilot to an LLM API "
                  "requires no structural changes. The sources files, copilot-instructions, "
                  "and answer format all stay identical. Only the backend changes.",
                  s["body"]),
              sp(3)]

    future_data = [
        ["Phase", "What changes", "What stays the same"],
        ["Now (PoC)", "User pastes question into Copilot Chat manually",
         "sources/ files, answer format, copilot-instructions"],
        ["Phase 2 (API)", "Script calls LLM API with same prompt + sources",
         "sources/ files, answer format, question syntax"],
        ["Phase 3 (UI)", "Web or CLI interface for non-technical users",
         "sources/ files, answer format, LLM backend"],
    ]
    ft = Table(future_data, colWidths=[CW*0.18, CW*0.41, CW*0.41])
    ft.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLUE_PALE, WHITE, GREEN_PALE]),
        ("TOPPADDING",    (0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8), ("VALIGN",(0,0),(-1,-1), "TOP"),
        ("BOX",           (0,0),(-1,-1), 0.5, GREY_RULE),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, GREY_RULE),
    ]))
    story += [ft, sp(3),
              Paragraph("When the API key is available, one script wraps it all:", s["h3"]),
              Paragraph(
                  "# future/query.py  — same sources, same prompt, automated\n"
                  "import os, yaml\n"
                  "from openai import OpenAI   # or anthropic, azure\n\n"
                  "client = OpenAI(api_key=os.environ['LLM_API_KEY'])\n"
                  "sources = yaml.safe_load(open('sources/veritas-infoscale.yaml'))\n"
                  "prompt  = build_prompt(app, version, kernel, sources)\n"
                  "answer  = client.chat.completions.create(model='gpt-4o', ...)\n"
                  "print(answer)   # same format as Copilot gives today",
                  s["code"])]

    doc.build(story, onFirstPage=on_any, onLaterPages=on_any)
    print(f"Architecture PDF → {out}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/architecture_guide.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
