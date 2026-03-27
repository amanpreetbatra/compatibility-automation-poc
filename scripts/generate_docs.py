#!/usr/bin/env python3
"""Generate a detailed architecture PDF for the compatibility automation tool."""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

# ── Palette ──────────────────────────────────────────────────────────────────
BLUE_DARK  = colors.HexColor("#1a2e4a")
BLUE_MID   = colors.HexColor("#2563eb")
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


# ── Custom Flowables ─────────────────────────────────────────────────────────

class PipelineBox(Flowable):
    """Horizontal pipeline of labelled boxes connected by arrows."""

    def __init__(self, steps, width, box_h=22*mm):
        super().__init__()
        self.steps = steps          # list of (label, sublabel, color)
        self.width = width
        self.box_h = box_h
        self.height = box_h + 6*mm

    def draw(self):
        n = len(self.steps)
        arrow_w = 6*mm
        total_arrow = arrow_w * (n - 1)
        box_w = (self.width - total_arrow) / n
        c = self.canv
        y0 = 3*mm

        for i, (label, sub, col) in enumerate(self.steps):
            x = i * (box_w + arrow_w)
            # box
            c.setFillColor(col)
            c.setStrokeColor(BLUE_DARK)
            c.setLineWidth(0.5)
            c.roundRect(x, y0, box_w, self.box_h, 3, fill=1, stroke=1)
            # label
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x + box_w/2, y0 + self.box_h/2 + 2, label)
            if sub:
                c.setFont("Helvetica", 5.5)
                c.drawCentredString(x + box_w/2, y0 + self.box_h/2 - 5, sub)
            # arrow
            if i < n - 1:
                ax = x + box_w
                ay = y0 + self.box_h/2
                c.setStrokeColor(BLUE_MID)
                c.setFillColor(BLUE_MID)
                c.setLineWidth(1.2)
                c.line(ax, ay, ax + arrow_w - 2, ay)
                # arrowhead
                c.setLineWidth(0)
                p = c.beginPath()
                tip = ax + arrow_w - 1
                p.moveTo(tip, ay)
                p.lineTo(tip - 3, ay + 2)
                p.lineTo(tip - 3, ay - 2)
                p.close()
                c.drawPath(p, fill=1, stroke=0)


class DecisionMatrix(Flowable):
    """Visual gating decision matrix with coloured rows."""

    ROWS = [
        ("Envelope widening",         "Lower min OR higher max than baseline",    RED,   RED_PALE,   "BLOCKED"),
        ("Ambiguous extraction",      "No explicit bounds found in docs",          RED,   RED_PALE,   "BLOCKED"),
        ("Low confidence",            "Confidence < high after extraction",        RED,   RED_PALE,   "BLOCKED"),
        ("Missing vendor source",     "No vendor_hcl / release_notes / advisory", AMBER, AMBER_PALE, "BLOCKED"),
        ("Envelope narrowing",        "Higher min AND lower max than baseline",    GREEN, GREEN_PALE, "ALLOWED"),
        ("Metadata-only change",      "Bounds unchanged, other fields differ",     BLUE_MID, BLUE_PALE, "INFO"),
        ("No change",                 "Identical to existing baseline",            GREY,  GREY_LIGHT, "SKIP"),
    ]

    def __init__(self, width):
        super().__init__()
        self.width = width
        row_h = 10*mm
        self.height = row_h * (len(self.ROWS) + 1) + 4*mm

    def draw(self):
        c = self.canv
        row_h = 10*mm
        col_w = [self.width * f for f in (0.28, 0.44, 0.16, 0.12)]
        headers = ["Change Type", "Condition", "Decision", "Label"]

        # header
        x = 0
        for i, (hdr, w) in enumerate(zip(headers, col_w)):
            c.setFillColor(BLUE_DARK)
            c.rect(x, self.height - row_h - 2*mm, w, row_h, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + w/2, self.height - row_h - 2*mm + 3, hdr)
            x += w

        for r, (change, cond, accent, bg, decision) in enumerate(self.ROWS):
            y = self.height - (r + 2) * row_h - 2*mm
            x = 0
            for ci, w in enumerate(col_w):
                c.setFillColor(bg)
                c.setStrokeColor(GREY_RULE)
                c.setLineWidth(0.4)
                c.rect(x, y, w, row_h, fill=1, stroke=1)
                x += w

            # text
            x = 2*mm
            c.setFillColor(BLUE_DARK)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(x, y + 3, change)
            x += col_w[0]
            c.setFont("Helvetica", 6.5)
            c.setFillColor(colors.black)
            c.drawString(x + 2*mm, y + 3, cond)
            x += col_w[1]
            # decision badge
            bw = col_w[2] - 4*mm
            bx = x + 2*mm
            c.setFillColor(accent)
            c.roundRect(bx, y + 1.5*mm, bw, 7*mm, 2, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(bx + bw/2, y + 3, decision)
            x += col_w[2]
            c.setFillColor(BLUE_DARK)
            c.setFont("Helvetica", 6.5)
            lbl = "auto-merge-blocked" if decision == "BLOCKED" else (
                  "auto-merge-allowed" if decision == "ALLOWED" else decision.lower())
            c.drawString(x + 1*mm, y + 3, lbl)


class FolderTree(Flowable):
    """Renders a folder tree diagram."""

    TREE = [
        ("configs/sources/",              0, BLUE_MID),
        ("  {id}.yaml",                   1, GREY),
        ("data/{id}/",                    0, BLUE_MID),
        ("  raw/",                        1, GREY),
        ("  parsed/",                     1, GREY),
        ("rules/",                        0, BLUE_MID),
        ("  baselines/{id}.yaml",         1, GREY),
        ("  generated/{id}.yaml",         1, GREY),
        ("tests/",                        0, BLUE_MID),
        ("  baselines/{id}_cases.yaml",   1, GREY),
        ("  generated/{id}_cases.yaml",   1, GREY),
        ("human_reviews/{id}/",           0, BLUE_MID),
        ("  YYYY-MM-DD_review.md",        1, GREY),
        ("  YYYY-MM-DD_response*.yaml",   1, GREY),
        ("scripts/",                      0, BLUE_MID),
        ("  lib/  query.py  human_review.py …",  1, GREY),
        (".vscode/tasks.json",            0, BLUE_MID),
        (".github/copilot-instructions.md", 0, BLUE_MID),
    ]

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = len(self.TREE) * 7*mm + 6*mm

    def draw(self):
        c = self.canv
        c.setFillColor(BLUE_PALE)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        y = self.height - 8*mm
        for text, indent, col in self.TREE:
            c.setFillColor(col)
            c.setFont("Courier-Bold" if indent == 0 else "Courier", 7.5)
            c.drawString(6*mm + indent * 8*mm, y, text)
            y -= 7*mm


class HumanReviewFlow(Flowable):
    """Illustrates the human review loop."""

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 58*mm

    def draw(self):
        c = self.canv
        W = self.width
        boxes = [
            (0.00, "extract_envelope\nambiguous",         RED_PALE,   RED),
            (0.22, "human_review.py\ngenerates prompt",   AMBER_PALE, AMBER),
            (0.44, "VS Code Copilot\nChat (user)",        BLUE_PALE,  BLUE_MID),
            (0.66, "ingest_review.py\nmerges response",   GREEN_PALE, GREEN),
            (0.84, "diff + tests\nre-generated",          GREY_LIGHT, GREY),
        ]
        bw = W * 0.18
        bh = 20*mm
        mid_y = 20*mm

        for fx, lbl, bg, border in boxes:
            bx = fx * W
            c.setFillColor(bg)
            c.setStrokeColor(border)
            c.setLineWidth(1)
            c.roundRect(bx, mid_y, bw, bh, 3, fill=1, stroke=1)
            c.setFillColor(BLUE_DARK)
            c.setFont("Helvetica-Bold", 6)
            lines = lbl.split("\n")
            for li, line in enumerate(lines):
                c.drawCentredString(bx + bw/2, mid_y + bh/2 + (0.5 - li) * 5, line)

        # arrows between boxes
        for i in range(len(boxes) - 1):
            fx = boxes[i][0] * W + bw
            tx = boxes[i+1][0] * W
            ay = mid_y + bh/2
            c.setStrokeColor(BLUE_MID)
            c.setFillColor(BLUE_MID)
            c.setLineWidth(1.2)
            c.line(fx, ay, tx - 2, ay)
            p = c.beginPath()
            p.moveTo(tx, ay)
            p.lineTo(tx - 3, ay + 2)
            p.lineTo(tx - 3, ay - 2)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

        # labels below
        labels = [
            (0.00, "Pipeline detects\nlow confidence"),
            (0.22, "Creates review.md\n+ response template"),
            (0.44, "User pastes prompt,\ngets YAML answer"),
            (0.66, "Updates baseline\nrule YAML"),
            (0.84, "Pipeline continues\nnormally"),
        ]
        c.setFont("Helvetica", 5.5)
        c.setFillColor(GREY)
        for fx, lbl in labels:
            bx = fx * W
            for li, line in enumerate(lbl.split("\n")):
                c.drawCentredString(bx + bw/2, mid_y - 7*mm + li * 5, line)

        # title
        c.setFillColor(BLUE_DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(W/2, self.height - 5*mm, "Human Review Loop (VS Code Copilot Integration)")


class VersionBox(Flowable):
    """Shows three version constraint types side by side."""

    TYPES = [
        ("kernel_range",     "RHEL kernels",    "4.18.0-193.el8\n         to\n4.18.0-425.el8", BLUE_MID),
        ("semver",           "Software pkgs",   "9.0.0\n  to\n9.1.4",                          GREEN),
        ("package_version",  "RPM/deb pkgs",    "8.0.2-1.el8\n    to\n8.0.5-3.el8",            AMBER),
    ]

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 38*mm

    def draw(self):
        c = self.canv
        bw = self.width / 3 - 4*mm
        bh = 30*mm
        for i, (typ, use, example, col) in enumerate(self.TYPES):
            bx = i * (self.width / 3)
            c.setFillColor(col)
            c.roundRect(bx, 0, bw, bh, 4, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(bx + bw/2, bh - 8, typ)
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(bx + bw/2, bh - 15, use)
            c.setFont("Courier", 7)
            for li, line in enumerate(example.split("\n")):
                c.drawCentredString(bx + bw/2, bh - 24 - li * 8, line)


# ── Style helpers ─────────────────────────────────────────────────────────────

def styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Normal"],
                             fontSize=26, textColor=BLUE_DARK, leading=32,
                             fontName="Helvetica-Bold", spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base["Normal"],
                             fontSize=14, textColor=BLUE_DARK, leading=18,
                             fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base["Normal"],
                             fontSize=10, textColor=BLUE_MID, leading=14,
                             fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"],
                               fontSize=9, textColor=colors.black, leading=14,
                               fontName="Helvetica", spaceAfter=4),
        "code": ParagraphStyle("code", parent=base["Normal"],
                               fontSize=7.5, textColor=BLUE_DARK, leading=11,
                               fontName="Courier", backColor=GREY_LIGHT,
                               leftIndent=8, rightIndent=8, spaceBefore=3, spaceAfter=3,
                               borderPad=4),
        "caption": ParagraphStyle("caption", parent=base["Normal"],
                                  fontSize=7.5, textColor=GREY, leading=10,
                                  fontName="Helvetica-Oblique", alignment=TA_CENTER,
                                  spaceBefore=2, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
                                 fontSize=9, textColor=colors.black, leading=13,
                                 fontName="Helvetica", leftIndent=12, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
                                   fontSize=13, textColor=GREY, leading=18,
                                   fontName="Helvetica-Oblique"),
        "cover_title": ParagraphStyle("cover_title", parent=base["Normal"],
                                      fontSize=32, textColor=WHITE, leading=40,
                                      fontName="Helvetica-Bold", alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"],
                                    fontSize=13, textColor=BLUE_LIGHT, leading=18,
                                    fontName="Helvetica", alignment=TA_CENTER),
        "cover_meta": ParagraphStyle("cover_meta", parent=base["Normal"],
                                     fontSize=9, textColor=BLUE_LIGHT, leading=13,
                                     fontName="Helvetica", alignment=TA_CENTER),
    }


def rule(color=GREY_RULE, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4)


def sp(h=4):
    return Spacer(1, h * mm)


# ── Cover page ────────────────────────────────────────────────────────────────

class CoverPage(Flowable):
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Background gradient simulation (dark blue)
        c.setFillColor(BLUE_DARK)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # Decorative circle
        c.setFillColor(colors.HexColor("#1e3a5f"))
        c.circle(self.width * 0.85, self.height * 0.75, 90, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#243d5c"))
        c.circle(self.width * 0.1, self.height * 0.15, 60, fill=1, stroke=0)

        # Accent bar
        c.setFillColor(BLUE_MID)
        c.rect(0, self.height * 0.42, self.width, 3, fill=1, stroke=0)

        # Title area
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(self.width/2, self.height * 0.62, "Compatibility")
        c.drawCentredString(self.width/2, self.height * 0.62 - 36, "Automation")
        c.setFillColor(BLUE_MID)
        c.drawCentredString(self.width/2, self.height * 0.62 - 72, "Platform")

        c.setFillColor(BLUE_LIGHT)
        c.setFont("Helvetica", 12)
        c.drawCentredString(self.width/2, self.height * 0.62 - 100,
                            "Architecture & Developer Guide")

        # Divider
        c.setStrokeColor(BLUE_MID)
        c.setLineWidth(1)
        c.line(self.width * 0.25, self.height * 0.42 - 20,
               self.width * 0.75, self.height * 0.42 - 20)

        # Meta
        c.setFillColor(BLUE_LIGHT)
        c.setFont("Helvetica", 9)
        c.drawCentredString(self.width/2, self.height * 0.42 - 40,
                            "Generic · Auditable · Deterministic · VS Code Copilot Integrated")

        # Bottom
        c.setFillColor(colors.HexColor("#1e3a5f"))
        c.rect(0, 0, self.width, 22*mm, fill=1, stroke=0)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.width/2, 10*mm, "compatibility-automation-poc  ·  2026")


# ── Page template helpers ─────────────────────────────────────────────────────

def on_first_page(canvas, doc):
    canvas.saveState()
    cover = CoverPage(W, H)
    cover.canv = canvas
    cover.draw()
    canvas.restoreState()


def on_page(canvas, doc):
    if doc.page == 1:
        on_first_page(canvas, doc)
        return
    canvas.saveState()
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN, H - 8*mm, "Compatibility Automation Platform")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - MARGIN, H - 8*mm, f"Page {doc.page}")
    canvas.setFillColor(GREY_RULE)
    canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W/2, 3*mm, "Confidential — Internal Use")
    canvas.restoreState()


# ── Document assembly ─────────────────────────────────────────────────────────

def build_pdf(out_path: Path) -> None:
    S = styles()
    content_w = W - 2 * MARGIN

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=18*mm, bottomMargin=14*mm,
        title="Compatibility Automation Platform — Architecture Guide",
        author="SRE Team",
    )

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    # Cover is drawn via onFirstPage; just push a full-page spacer then break
    story.append(Spacer(1, H - 2 * MARGIN))
    story.append(PageBreak())

    # ── Table of Contents ──────────────────────────────────────────────────────
    story.append(sp(6))
    story.append(Paragraph("Table of Contents", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    toc_items = [
        ("1.", "Executive Summary"),
        ("2.", "System Architecture Overview"),
        ("3.", "Pipeline — Step by Step"),
        ("4.", "Generic Configuration"),
        ("5.", "Version Constraint Types"),
        ("6.", "Safety & Gating Policy"),
        ("7.", "Human Review with VS Code Copilot"),
        ("8.", "File Layout Reference"),
        ("9.", "Query CLI Reference"),
        ("10.", "Adding a New Product"),
        ("11.", "Script Reference"),
        ("12.", "GitHub Actions Workflow"),
    ]
    toc_data = [[Paragraph(f"<b>{n}</b>", S["body"]), Paragraph(title, S["body"])]
                for n, title in toc_items]
    toc_table = Table(toc_data, colWidths=[12*mm, content_w - 12*mm])
    toc_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ── 1. Executive Summary ───────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "The Compatibility Automation Platform is a <b>product-agnostic</b>, "
        "<b>deterministic</b>, and <b>auditable</b> system for tracking whether a given "
        "software product version is certified to run on a specific platform version. "
        "It replaces manual spreadsheet tracking with an automated pipeline that:",
        S["body"]))
    story.append(sp(1))
    bullets = [
        "Fetches vendor compatibility documents (HCLs, release notes, advisories) automatically.",
        "Extracts the exact supported version range using conservative, deterministic rules — no inference.",
        "Compares every change against a versioned baseline and classifies it as safe (narrowing) or unsafe (widening/ambiguous).",
        "Answers instant queries: <i>\"Is veritas-infoscale 8.0.2 compatible with RHEL 8 kernel 4.18.0-305.el8?\"</i>",
        "Integrates VS Code GitHub Copilot for human-in-the-loop review when automation is not confident — no external API keys required.",
        "Runs end-to-end in GitHub Actions on a weekly schedule, with per-product matrix parallelism.",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", S["bullet"]))

    story.append(sp(4))
    kpi_data = [
        ["Metric", "Value"],
        ["Supported version types", "kernel_range · semver · package_version"],
        ["AI dependency", "VS Code GitHub Copilot (no API keys needed)"],
        ["Auto-merge safety", "Widening changes always blocked"],
        ["Audit trail", "SHA-256 hashes + provenance JSON per file"],
        ["CI cadence", "Weekly (Monday 03:00 UTC) + manual dispatch"],
        ["Adding a new product", "One YAML config file"],
    ]
    kpi_table = Table(kpi_data, colWidths=[content_w * 0.38, content_w * 0.62])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(kpi_table)
    story.append(PageBreak())

    # ── 2. System Architecture ─────────────────────────────────────────────────
    story.append(Paragraph("2. System Architecture Overview", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "The system is organized around a <b>config ID</b> — a slug that identifies a "
        "product+platform pair (e.g., <font face='Courier'>veritas-infoscale_rhel</font>). "
        "Every file in the system is namespaced under this ID, which means multiple products "
        "and platforms can coexist with zero interference.",
        S["body"]))
    story.append(sp(3))

    # Architecture pipeline boxes
    pipeline_steps = [
        ("Vendor\nDocs", "HCL / RN / Advisories", colors.HexColor("#7c3aed")),
        ("Fetch\nSources", "fetch_sources.py", BLUE_MID),
        ("Detect\nChanges", "SHA-256 hash", colors.HexColor("#0891b2")),
        ("Extract\nText", "PDF/HTML→TXT", colors.HexColor("#059669")),
        ("Extract\nEnvelope", "min/max bounds", GREEN),
        ("Diff\nRules", "vs baseline", AMBER),
        ("Generate\nTests", "GO/NO_GO", colors.HexColor("#dc2626")),
        ("Create\nPR Body", "gate decision", BLUE_DARK),
    ]
    story.append(PipelineBox(pipeline_steps, content_w, box_h=20*mm))
    story.append(Paragraph("Figure 1 — Main automation pipeline", S["caption"]))
    story.append(sp(4))

    story.append(Paragraph(
        "The pipeline has two execution paths depending on whether automated extraction "
        "succeeds with high confidence:",
        S["body"]))
    story.append(sp(2))

    path_data = [
        ["Path", "Trigger", "Outcome"],
        ["Automated (happy path)",
         "Docs contain explicit version bounds with support phrase on same line",
         "Rule updated, tests generated, PR created automatically"],
        ["Human review (Copilot)",
         "No docs, ambiguous extraction, or confidence < high",
         "Review prompt generated → user + Copilot fill template → pipeline resumes"],
    ]
    path_table = Table(path_data, colWidths=[content_w*0.22, content_w*0.42, content_w*0.36])
    path_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [GREEN_PALE, AMBER_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(path_table)
    story.append(PageBreak())

    # ── 3. Pipeline Step by Step ───────────────────────────────────────────────
    story.append(Paragraph("3. Pipeline — Step by Step", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))

    steps = [
        ("fetch_sources.py", BLUE_MID,
         "Downloads vendor documents from URLs listed in <font face='Courier'>configs/sources/{id}.yaml</font> "
         "into <font face='Courier'>data/{id}/raw/</font>. Writes a <font face='Courier'>.provenance.json</font> "
         "sidecar per file recording the URL, download timestamp, and SHA-256 hash. "
         "Supports local file copy (<font face='Courier'>local_path</font>) and HTTP download.",
         "python3 scripts/fetch_sources.py --config-id veritas-infoscale_rhel"),
        ("detect_changes.py", colors.HexColor("#0891b2"),
         "Hashes every file in <font face='Courier'>data/{id}/raw/</font> using SHA-256 and compares "
         "against the previous run's state in <font face='Courier'>ingest_state.json</font>. "
         "Produces <font face='Courier'>pending.json</font> — the list of files that changed and must "
         "be re-extracted. Unchanged files are skipped.",
         "python3 scripts/detect_changes.py --config-id veritas-infoscale_rhel"),
        ("extract_text.py", colors.HexColor("#059669"),
         "Converts each pending raw file to plain text in <font face='Courier'>data/{id}/parsed/</font>. "
         "TXT files are copied directly. PDF and HTML are currently stubbed with an "
         "<font face='Courier'>EXTRACTION_PENDING</font> marker — add parsers (pdfminer, beautifulsoup) "
         "as needed. Updates <font face='Courier'>manifest.json</font> with raw→parsed mappings.",
         "python3 scripts/extract_text.py --config-id veritas-infoscale_rhel"),
        ("extract_envelope.py", GREEN,
         "The core extraction step. Applies the <font face='Courier'>version_regex</font> from the config "
         "to each parsed text file, looking for lines that contain both a support phrase "
         "(<i>support / certified / compatible</i>) AND two or more version strings. "
         "Confidence is <b>high</b> when both conditions are met on the same line, "
         "<b>medium</b> when versions are found without the phrase, and <b>low</b> when nothing is found. "
         "Writes the result to <font face='Courier'>rules/generated/{id}.yaml</font> and prints "
         "<font face='Courier'>HUMAN_REVIEW_NEEDED</font> if confidence is not high.",
         "python3 scripts/extract_envelope.py --config-id veritas-infoscale_rhel"),
        ("diff_rules.py", AMBER,
         "Loads the generated rule and the baseline rule and compares their version bounds "
         "using <font face='Courier'>VersionComparator</font> (tuple comparison — not string comparison). "
         "Classifies the change as widening, narrowing, or ambiguous. Also checks confidence, "
         "vendor source presence, and ambiguity flag. Writes <font face='Courier'>diff_summary.json</font>.",
         "python3 scripts/diff_rules.py --config-id veritas-infoscale_rhel"),
        ("generate_tests.py", RED,
         "Creates GO and NO_GO test cases from the generated rule's bounds. Uses "
         "<font face='Courier'>VersionComparator.bump()</font> to produce an above-max version for the "
         "NO_GO case — this works generically for any version format. "
         "Writes to <font face='Courier'>tests/generated/{id}_cases.yaml</font>.",
         "python3 scripts/generate_tests.py --config-id veritas-infoscale_rhel"),
        ("create_pr.py", BLUE_DARK,
         "Reads <font face='Courier'>diff_summary.json</font> and produces a Markdown PR body with a "
         "gating decision table. The gate is <b>pr_block_auto_merge</b> if any config has a blocking "
         "decision, <b>pr_allowed</b> if all are narrowing with high confidence, or <b>info</b> for "
         "metadata-only changes. Does not push to GitHub directly — wire to <font face='Courier'>gh</font> CLI in CI.",
         "python3 scripts/create_pr.py --config-id veritas-infoscale_rhel"),
    ]

    for i, (name, col, desc, cmd) in enumerate(steps):
        story.append(KeepTogether([
            Paragraph(f"Step {i+1}: {name}", S["h3"]),
            Paragraph(desc, S["body"]),
            Paragraph(cmd, S["code"]),
            sp(2),
        ]))

    story.append(PageBreak())

    # ── 4. Generic Configuration ───────────────────────────────────────────────
    story.append(Paragraph("4. Generic Configuration", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "Each product+platform pair is described by a single YAML config file. "
        "The entire pipeline reads from this config — no hardcoded product names, "
        "version strings, or regex patterns exist in the scripts.",
        S["body"]))
    story.append(sp(2))

    story.append(Paragraph("Source Config  (configs/sources/{id}.yaml)", S["h3"]))
    story.append(Paragraph(
        "id: veritas-infoscale_rhel\n"
        "product:\n"
        "  name: veritas-infoscale\n"
        "  version: \"8.0.2\"\n"
        "platform:\n"
        "  name: rhel\n"
        "  version: \"8\"\n"
        "version_constraint:\n"
        "  type: kernel_range\n"
        "  version_regex: '\\d+\\.\\d+\\.\\d+-(\\d+)\\.el\\d+'\n"
        "  comparison_groups: [1]   # only the build number matters for ordering\n"
        "sources:\n"
        "  - name: veritas_hcl_oct2023\n"
        "    url: \"\"               # URL to download\n"
        "    type: vendor_hcl\n"
        "    local_path: \"\"        # or path to local file",
        S["code"]))
    story.append(sp(3))

    story.append(Paragraph("Baseline Rule  (rules/baselines/{id}.yaml — schema v2.0)", S["h3"]))
    story.append(Paragraph(
        "schema_version: \"2.0\"\n"
        "id: veritas-infoscale_rhel\n"
        "product: {name: veritas-infoscale, version: \"8.0.2\"}\n"
        "platform: {name: rhel, version: \"8\"}\n"
        "compatibility:\n"
        "  status: supported\n"
        "  version_constraint:\n"
        "    type: kernel_range\n"
        "    min: 4.18.0-193.el8\n"
        "    max: 4.18.0-425.el8\n"
        "    unsupported_examples: [4.18.0-80.el8, 4.18.0-477.el8]\n"
        "notes:\n"
        "  risk: \"Storage/clustering instability outside envelope\"\n"
        "  remediation: \"Stay within envelope or get vendor confirmation\"\n"
        "metadata:\n"
        "  sources: [{name: Veritas HCL Oct 2023, type: vendor_hcl}]\n"
        "  confidence: medium      # high | medium | low | unknown\n"
        "  owner: sre-team\n"
        "  last_reviewed: \"2026-01-30\"\n"
        "  review_interval_days: 90\n"
        "  ambiguous: false",
        S["code"]))
    story.append(PageBreak())

    # ── 5. Version Constraint Types ────────────────────────────────────────────
    story.append(Paragraph("5. Version Constraint Types", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "The <font face='Courier'>VersionComparator</font> class in "
        "<font face='Courier'>scripts/lib/version_compare.py</font> provides generic version parsing, "
        "comparison, and bumping. It is driven entirely by the config's "
        "<font face='Courier'>version_constraint</font> block — no product-specific code exists in the scripts.",
        S["body"]))
    story.append(sp(3))
    story.append(VersionBox(content_w))
    story.append(Paragraph("Figure 2 — The three supported version constraint types", S["caption"]))
    story.append(sp(4))

    vc_data = [
        ["Type", "version_regex example", "comparison_groups", "Used for"],
        ["kernel_range",    r"\d+\.\d+\.\d+-(\d+)\.el\d+",  "[1]",      "RHEL kernel build number"],
        ["semver",          r"(\d+)\.(\d+)\.(\d+)",          "[1, 2, 3]","Standard semantic versions"],
        ["package_version", r"(\d+)\.(\d+)\.(\d+)-(\d+)",   "[1,2,3,4]","RPM/deb package releases"],
    ]
    vc_table = Table(vc_data, colWidths=[content_w*0.18, content_w*0.34, content_w*0.20, content_w*0.28])
    vc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0, 1), (-1, -1), "Courier"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(vc_table)
    story.append(sp(4))

    story.append(Paragraph("How VersionComparator works", S["h3"]))
    story.append(Paragraph(
        "All comparison reduces to comparing tuples of integers. The regex captures groups, "
        "and <font face='Courier'>comparison_groups</font> selects which groups to use for ordering. "
        "For RHEL kernels, only group 1 (the build ID after the dash) is used because the "
        "<font face='Courier'>4.18.0</font> prefix and <font face='Courier'>el8</font> suffix are "
        "invariant within a platform version.",
        S["body"]))
    story.append(Paragraph(
        "# kernel 4.18.0-425.el8 → parse → (425,)\n"
        "# kernel 4.18.0-477.el8 → parse → (477,)\n"
        "# is_within(\"4.18.0-305.el8\", \"4.18.0-193.el8\", \"4.18.0-425.el8\")\n"
        "#   (305,) within [(193,), (425,)] → True  →  COMPATIBLE\n\n"
        "# bump(\"4.18.0-425.el8\") → \"4.18.0-426.el8\"  (for NO_GO test case)",
        S["code"]))
    story.append(PageBreak())

    # ── 6. Safety & Gating ────────────────────────────────────────────────────
    story.append(Paragraph("6. Safety & Gating Policy", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "The system is conservative by design: any change that could increase risk is "
        "automatically blocked. Only changes that reduce risk (narrowing) or are purely "
        "informational can proceed without human approval.",
        S["body"]))
    story.append(sp(3))
    story.append(DecisionMatrix(content_w))
    story.append(Paragraph("Figure 3 — Gating decision matrix", S["caption"]))
    story.append(sp(4))

    story.append(Paragraph("Confidence levels", S["h3"]))
    conf_data = [
        ["Level", "Condition", "Auto-merge?"],
        ["high",    "Support phrase + 2 version strings on the same line", "Narrowing only"],
        ["medium",  "2 version strings found but no explicit support phrase", "No — blocked"],
        ["low",     "Fewer than 2 version strings found in any document",   "No — blocked"],
        ["unknown", "No documents processed or rule not yet established",    "No — blocked"],
    ]
    conf_table = Table(conf_data, colWidths=[content_w*0.12, content_w*0.63, content_w*0.25])
    conf_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [GREEN_PALE, AMBER_PALE, RED_PALE, GREY_LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(conf_table)
    story.append(PageBreak())

    # ── 7. Human Review / Copilot ──────────────────────────────────────────────
    story.append(Paragraph("7. Human Review with VS Code Copilot", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "When automation cannot extract version bounds with high confidence, the system "
        "falls back to a structured human review loop. No external AI API keys are required — "
        "the user pastes a generated prompt into <b>VS Code GitHub Copilot Chat</b>.",
        S["body"]))
    story.append(sp(3))
    story.append(HumanReviewFlow(content_w))
    story.append(Paragraph("Figure 4 — Human review loop using VS Code Copilot", S["caption"]))
    story.append(sp(4))

    story.append(Paragraph("Step-by-step human review", S["h3"]))
    review_steps = [
        ("1", "Pipeline detects ambiguity",
         "extract_envelope.py prints HUMAN_REVIEW_NEEDED to stdout. "
         "GitHub Actions detects this and runs human_review.py automatically."),
        ("2", "Review files generated",
         "human_review.py creates two files in human_reviews/{id}/:\n"
         "  • YYYY-MM-DD_review.md — the Copilot Chat prompt to paste\n"
         "  • YYYY-MM-DD_response_template.yaml — pre-filled template to complete"),
        ("3", "User opens in VS Code",
         "Open the review.md file. Open Copilot Chat (Ctrl+Shift+I). "
         "Optionally attach the vendor PDF/HTML. Paste the prompt and send."),
        ("4", "Fill the response template",
         "Copy Copilot's YAML output into the response_template.yaml. "
         "The template already has current baseline values as defaults — "
         "only override what Copilot provides."),
        ("5", "Ingest the response",
         "Run ingest_review.py --config-id <id> --review <template.yaml>. "
         "This deep-merges the response into the baseline, sets ambiguous=false, "
         "updates last_reviewed, and re-runs diff + test generation."),
        ("6", "Pipeline resumes",
         "create_pr.py picks up the updated diff_summary.json and produces "
         "a PR body with the corrected gating decision."),
    ]

    for num, title, detail in review_steps:
        story.append(KeepTogether([
            Table([[
                Paragraph(f"<b>{num}</b>", ParagraphStyle("badge", parent=S["body"],
                    textColor=WHITE, alignment=TA_CENTER)),
                Paragraph(f"<b>{title}</b><br/>{detail}", S["body"]),
            ]], colWidths=[8*mm, content_w - 8*mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), BLUE_MID),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("ROUNDEDCORNERS", [3]),
            ])),
            sp(1),
        ]))

    story.append(PageBreak())

    # ── 8. File Layout ─────────────────────────────────────────────────────────
    story.append(Paragraph("8. File Layout Reference", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(FolderTree(content_w))
    story.append(Paragraph("Figure 5 — Repository file layout", S["caption"]))
    story.append(sp(4))

    file_data = [
        ["Path pattern", "Description"],
        ["configs/sources/{id}.yaml",         "Product+platform config: version_regex, sources, notes"],
        ["data/{id}/raw/",                     "Downloaded vendor docs (PDF, HTML, TXT)"],
        ["data/{id}/parsed/",                  "Extracted text, ingest_state.json, pending.json, manifest.json"],
        ["rules/baselines/{id}.yaml",          "Authoritative baseline rule (schema v2.0, manually maintained)"],
        ["rules/generated/{id}.yaml",          "Auto-extracted rule produced by extract_envelope.py"],
        ["tests/baselines/{id}_cases.yaml",    "Hand-written GO/NO_GO test cases"],
        ["tests/generated/{id}_cases.yaml",    "Auto-generated test cases from version bounds"],
        ["human_reviews/{id}/",               "Copilot review prompts and response templates"],
        ["scripts/lib/version_compare.py",     "VersionComparator: parse, is_within, bump, compare"],
        ["scripts/lib/config_loader.py",       "load_config(), list_config_ids(), validation"],
        ["scripts/lib/path_resolver.py",       "All file paths — single source of truth"],
        ["scripts/query.py",                   "CLI query: exit 0=COMPATIBLE 1=NOT_COMPATIBLE 2=UNKNOWN"],
        ["scripts/human_review.py",            "Generate Copilot review prompt + response template"],
        ["scripts/ingest_review.py",           "Merge Copilot response into baseline, re-run diff+tests"],
        [".vscode/tasks.json",                 "5 VS Code tasks: query, pipeline, open reviews"],
        [".github/copilot-instructions.md",    "Copilot context: schemas, rules, expected output format"],
    ]
    file_table = Table(file_data, colWidths=[content_w*0.44, content_w*0.56])
    file_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0, 1), (0, -1), "Courier"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(file_table)
    story.append(PageBreak())

    # ── 9. Query CLI ──────────────────────────────────────────────────────────
    story.append(Paragraph("9. Query CLI Reference", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "<font face='Courier'>scripts/query.py</font> is the primary user-facing feature. "
        "It reads all baseline rules and answers compatibility questions in under a second.",
        S["body"]))
    story.append(sp(2))

    story.append(Paragraph("Basic query", S["h3"]))
    story.append(Paragraph(
        "python3 scripts/query.py \\\n"
        "  --product veritas-infoscale \\\n"
        "  --platform rhel \\\n"
        "  --version 4.18.0-305.el8",
        S["code"]))

    story.append(Paragraph("Scoped to specific versions", S["h3"]))
    story.append(Paragraph(
        "python3 scripts/query.py \\\n"
        "  --product veritas-infoscale --product-version 8.0.2 \\\n"
        "  --platform rhel --platform-version 8 \\\n"
        "  --version 4.18.0-477.el8",
        S["code"]))

    story.append(Paragraph("JSON output (for scripting)", S["h3"]))
    story.append(Paragraph(
        "python3 scripts/query.py --product veritas-infoscale \\\n"
        "  --platform rhel --version 4.18.0-305.el8 --json",
        S["code"]))

    story.append(sp(3))
    exit_data = [
        ["Exit code", "Meaning", "Use case"],
        ["0", "COMPATIBLE",     "Version is within the documented supported range"],
        ["1", "NOT_COMPATIBLE", "Version is outside the range or product is unsupported"],
        ["2", "UNKNOWN",        "No rule found — run the pipeline or add a config"],
    ]
    exit_table = Table(exit_data, colWidths=[content_w*0.15, content_w*0.25, content_w*0.60])
    exit_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [GREEN_PALE, RED_PALE, AMBER_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(exit_table)
    story.append(PageBreak())

    # ── 10. Adding a New Product ───────────────────────────────────────────────
    story.append(Paragraph("10. Adding a New Product", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "Adding support for a new product+platform pair requires <b>one config file</b> and "
        "optionally a baseline rule. No script changes are needed — the pipeline discovers "
        "new configs automatically.",
        S["body"]))
    story.append(sp(2))

    new_steps = [
        "Create <font face='Courier'>configs/sources/{new-id}.yaml</font> with product, platform, version_regex, and sources.",
        "Optionally create <font face='Courier'>rules/baselines/{new-id}.yaml</font> if you already know the bounds.",
        "Add <font face='Courier'>\"{new-id}\"</font> to the <font face='Courier'>options</font> array in <font face='Courier'>.vscode/tasks.json</font>.",
        "Run <font face='Courier'>python3 scripts/fetch_sources.py --config-id {new-id}</font> to download vendor docs.",
        "Run the full pipeline. If extraction is ambiguous, run <font face='Courier'>human_review.py</font> and use Copilot.",
        "Commit <font face='Courier'>configs/sources/{new-id}.yaml</font> and <font face='Courier'>rules/baselines/{new-id}.yaml</font>.",
        "GitHub Actions will pick up the new config on the next scheduled run automatically.",
    ]
    for i, s in enumerate(new_steps):
        story.append(Paragraph(f"{i+1}. {s}", S["bullet"]))

    story.append(sp(3))
    story.append(Paragraph("Example: Oracle DB 19c on RHEL 8", S["h3"]))
    story.append(Paragraph(
        "id: oracle-db_rhel\n"
        "product:\n"
        "  name: oracle-db\n"
        "  version: \"19c\"\n"
        "platform:\n"
        "  name: rhel\n"
        "  version: \"8\"\n"
        "version_constraint:\n"
        "  type: semver\n"
        "  version_regex: '(\\d+)\\.(\\d+)\\.(\\d+)'\n"
        "  comparison_groups: [1, 2, 3]\n"
        "sources:\n"
        "  - name: oracle_cert_matrix_2026\n"
        "    url: \"\"          # paste URL when available\n"
        "    type: vendor_hcl",
        S["code"]))
    story.append(PageBreak())

    # ── 11. Script Reference ───────────────────────────────────────────────────
    story.append(Paragraph("11. Script Reference", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))

    scripts_ref = [
        ("query.py",             "Query",      "Answer: is product X version Y compatible?\nArgs: --product --platform --version [--product-version] [--platform-version] [--json]"),
        ("fetch_sources.py",     "Fetch",      "Download vendor docs from URLs in config.\nArgs: [--config-id]"),
        ("detect_changes.py",    "Detect",     "Hash raw files, produce pending.json.\nArgs: [--config-id]"),
        ("extract_text.py",      "Extract",    "Convert raw files to plain text.\nArgs: [--config-id]"),
        ("extract_envelope.py",  "Envelope",   "Parse min/max version bounds from text. Prints HUMAN_REVIEW_NEEDED if ambiguous.\nArgs: [--config-id]"),
        ("diff_rules.py",        "Diff",       "Compare generated vs baseline using VersionComparator. Write diff_summary.json.\nArgs: [--config-id]"),
        ("generate_tests.py",    "Tests",      "Build GO/NO_GO test YAML using VersionComparator.bump().\nArgs: [--config-id]"),
        ("create_pr.py",         "PR",         "Produce pr_body.md with gating table. Does not call GitHub API.\nArgs: [--config-id]"),
        ("human_review.py",      "Review",     "Generate Copilot Chat prompt + response template in human_reviews/{id}/.\nArgs: --config-id"),
        ("ingest_review.py",     "Ingest",     "Deep-merge Copilot response into baseline. Re-runs diff + test generation.\nArgs: --config-id --review <path>"),
        ("migrate_legacy.py",    "Migrate",    "One-time: convert old docs/ structure to new data/ layout. Run once."),
    ]
    script_data = [["Script", "Role", "Description"]] + scripts_ref
    script_table = Table(script_data, colWidths=[content_w*0.26, content_w*0.12, content_w*0.62])
    script_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0, 1), (0, -1), "Courier"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(script_table)
    story.append(PageBreak())

    # ── 12. GitHub Actions ─────────────────────────────────────────────────────
    story.append(Paragraph("12. GitHub Actions Workflow", S["h1"]))
    story.append(rule(BLUE_MID, 1.5))
    story.append(sp(2))
    story.append(Paragraph(
        "The workflow at <font face='Courier'>.github/workflows/compatibility-update.yml</font> "
        "runs on a weekly schedule and on manual dispatch. It uses a <b>dynamic matrix strategy</b> "
        "— the list of configs is read at runtime from <font face='Courier'>configs/sources/*.yaml</font>, "
        "so adding a new product requires no workflow changes.",
        S["body"]))
    story.append(sp(3))

    story.append(Paragraph("Job structure", S["h3"]))
    job_data = [
        ["Job", "Purpose"],
        ["setup",                  "Reads configs/sources/*.yaml, builds matrix of config IDs"],
        ["compatibility-update",   "Runs once per config ID (parallel, fail-fast: false)"],
    ]
    job_table = Table(job_data, colWidths=[content_w*0.30, content_w*0.70])
    job_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(job_table)
    story.append(sp(3))

    story.append(Paragraph("Per-config steps", S["h3"]))
    ci_steps = [
        ("Checkout + Python setup",       "actions/checkout@v4, setup-python@v5 (3.11)"),
        ("Install deps",                   "pip install pyyaml requests"),
        ("fetch_sources.py",               "Download vendor docs"),
        ("detect_changes.py",              "Hash and queue changed files"),
        ("extract_text.py",                "Convert to plain text"),
        ("extract_envelope.py",            "Parse bounds; set needs_review=true if HUMAN_REVIEW_NEEDED in stdout"),
        ("human_review.py (conditional)",  "Only runs if needs_review=true; uploads review files as artifact"),
        ("diff_rules.py",                  "Compare to baseline"),
        ("generate_tests.py",              "Generate test cases"),
        ("create_pr.py",                   "Produce PR body"),
        ("Upload artifacts",               "rules/generated/, tests/generated/, data/{id}/parsed/, human_reviews/{id}/"),
    ]
    ci_data = [["Step", "Detail"]] + [[s, d] for s, d in ci_steps]
    ci_table = Table(ci_data, colWidths=[content_w*0.38, content_w*0.62])
    ci_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BLUE_PALE]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_RULE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_RULE),
    ]))
    story.append(ci_table)
    story.append(sp(3))

    story.append(Paragraph("Manual dispatch", S["h3"]))
    story.append(Paragraph(
        "Go to <b>Actions → Compatibility Update → Run workflow</b> and enter a config ID "
        "(e.g., <font face='Courier'>veritas-infoscale_rhel</font>) to run a single config. "
        "Leave blank to run all configs.",
        S["body"]))

    story.append(sp(4))
    story.append(rule(BLUE_MID, 1))
    story.append(sp(2))
    story.append(Paragraph(
        "For questions or contributions, see the repository README or open a GitHub issue.",
        ParagraphStyle("footer_note", parent=S["body"], textColor=GREY, alignment=TA_CENTER)))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF written to: {out_path}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/architecture_guide.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(out)
