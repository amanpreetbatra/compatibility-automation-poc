#!/usr/bin/env python3
"""Generate the stakeholder presentation for the Compatibility Checker PoC."""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt, Emu

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY        = RGBColor(0x0f, 0x20, 0x44)
BLUE        = RGBColor(0x1d, 0x4e, 0xd8)
BLUE_LIGHT  = RGBColor(0xdb, 0xe4, 0xfe)
BLUE_PALE   = RGBColor(0xef, 0xf6, 0xff)
GREEN       = RGBColor(0x16, 0xa3, 0x4a)
GREEN_PALE  = RGBColor(0xdc, 0xfc, 0xe7)
RED         = RGBColor(0xdc, 0x26, 0x26)
RED_PALE    = RGBColor(0xfe, 0xe2, 0xe2)
AMBER       = RGBColor(0xd9, 0x77, 0x06)
AMBER_PALE  = RGBColor(0xfe, 0xf3, 0xc7)
GREY        = RGBColor(0x6b, 0x72, 0x80)
GREY_LIGHT  = RGBColor(0xf3, 0xf4, 0xf6)
WHITE       = RGBColor(0xff, 0xff, 0xff)

SW = Inches(13.33)
SH = Inches(7.5)


# ── Shape helpers ─────────────────────────────────────────────────────────────
def add_rect(slide, l, t, w, h, fill, line=None, radius=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(l), Inches(t), Inches(w), Inches(h)
    )
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    if line:
        shape.line.color.rgb = line; shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape


def add_text(slide, text, l, t, w, h, size=18, bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, wrap=True, italic=False):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size = Pt(size); run.font.bold = bold
    run.font.color.rgb = color; run.font.italic = italic
    return tb


def add_bullet_box(slide, title, bullets, l, t, w, h, bg=BLUE_PALE, title_color=NAVY,
                   bullet_color=NAVY, title_size=12, bullet_size=10):
    add_rect(slide, l, t, w, h, bg)
    add_text(slide, title, l+0.1, t+0.08, w-0.2, 0.3,
             size=title_size, bold=True, color=title_color)
    for i, b in enumerate(bullets):
        add_text(slide, f"• {b}", l+0.12, t+0.38+i*0.28, w-0.22, 0.28,
                 size=bullet_size, color=bullet_color)


def slide_bg(slide, color=NAVY):
    bg = slide.background; fill = bg.fill
    fill.solid(); fill.fore_color.rgb = color


def title_bar(slide, title, subtitle=None):
    add_rect(slide, 0, 0, 13.33, 1.2, NAVY)
    add_text(slide, title, 0.4, 0.15, 11, 0.6, size=28, bold=True,
             color=WHITE, align=PP_ALIGN.LEFT)
    if subtitle:
        add_text(slide, subtitle, 0.4, 0.75, 11, 0.35, size=13,
                 color=BLUE_LIGHT, align=PP_ALIGN.LEFT)
    # accent line
    add_rect(slide, 0, 1.2, 13.33, 0.04, BLUE)


def slide_num(slide, n):
    add_text(slide, str(n), 12.8, 7.1, 0.4, 0.3, size=9, color=GREY, align=PP_ALIGN.RIGHT)


# ── Slides ────────────────────────────────────────────────────────────────────

def slide_cover(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    slide_bg(sl, NAVY)
    add_rect(sl, 0, 2.8, 13.33, 0.06, BLUE)
    add_rect(sl, 0, 0, 13.33, 2.8, NAVY)
    add_rect(sl, 9.5, 0, 3.83, 7.5, RGBColor(0x16, 0x2a, 0x55))

    add_text(sl, "Compatibility Checker", 0.5, 1.0, 9, 1.0,
             size=40, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    add_text(sl, "Copilot PoC", 0.5, 2.0, 9, 0.6,
             size=22, bold=True, color=BLUE_LIGHT, align=PP_ALIGN.LEFT)
    add_text(sl, "Know before you patch.", 0.5, 3.1, 9, 0.5,
             size=16, color=RGBColor(0x93, 0xc5, 0xfd), align=PP_ALIGN.LEFT, italic=True)
    add_text(sl, "Infrastructure Reliability  ·  2026", 0.5, 6.9, 6, 0.4,
             size=9, color=GREY, align=PP_ALIGN.LEFT)

    # right panel content
    for i, line in enumerate(["Ask", "Search", "Know"]):
        add_text(sl, line, 10.0, 1.8 + i*1.5, 2.8, 0.8,
                 size=26, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(sl, "Before every patch", 9.7, 6.5, 3.4, 0.4,
             size=9, color=GREY, align=PP_ALIGN.CENTER, italic=True)


def slide_problem(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    title_bar(sl, "The Problem", "Patching is risky when compatibility is unknown")
    slide_num(sl, 2)

    add_text(sl, "Before every kernel patch, engineers must manually verify compatibility with every installed enterprise application.",
             0.4, 1.4, 12.5, 0.5, size=12, color=NAVY)

    steps = [
        ("1", "Open vendor HCL page", "e.g. veritas.com/support"),
        ("2", "Search release notes", "for kernel version range"),
        ("3", "Check Red Hat advisories", "cross-reference multiple docs"),
        ("4", "Document findings", "manually in a spreadsheet"),
    ]
    for i, (num, title, sub) in enumerate(steps):
        x = 0.3 + i * 3.2
        add_rect(sl, x, 2.1, 2.9, 1.4, BLUE_PALE, line=BLUE)
        add_rect(sl, x, 2.1, 0.5, 1.4, BLUE)
        add_text(sl, num, x, 2.1, 0.5, 1.4, size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_text(sl, title, x+0.55, 2.25, 2.3, 0.4, size=10, bold=True, color=NAVY)
        add_text(sl, sub,   x+0.55, 2.65, 2.3, 0.5, size=9, color=GREY)

        if i < 3:
            add_text(sl, "→", x+3.0, 2.55, 0.25, 0.4, size=16, bold=True, color=BLUE, align=PP_ALIGN.CENTER)

    add_rect(sl, 0.3, 3.8, 12.5, 0.8, RGBColor(0xfe, 0xf3, 0xc7), line=AMBER)
    add_text(sl, "⏱  30–60 minutes per patch window  ·  Error-prone  ·  Undocumented  ·  Repeated every time",
             0.5, 3.9, 12.1, 0.5, size=12, bold=True, color=AMBER, align=PP_ALIGN.CENTER)

    add_rect(sl, 0.3, 4.9, 5.8, 1.9, RED_PALE, line=RED)
    add_text(sl, "Without this check:", 0.5, 5.0, 5.4, 0.35, size=11, bold=True, color=RED)
    for i, b in enumerate(["Application crashes post-patch", "Emergency rollbacks", "Unplanned downtime"]):
        add_text(sl, f"✗  {b}", 0.5, 5.4+i*0.38, 5.4, 0.35, size=10, color=RED)

    add_rect(sl, 7.2, 4.9, 5.8, 1.9, GREEN_PALE, line=GREEN)
    add_text(sl, "With this check:", 7.4, 5.0, 5.4, 0.35, size=11, bold=True, color=GREEN)
    for i, b in enumerate(["Patch with confidence", "Documented evidence", "Faster patch cycles"]):
        add_text(sl, f"✓  {b}", 7.4, 5.4+i*0.38, 5.4, 0.35, size=10, color=GREEN)


def slide_solution(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    title_bar(sl, "The Solution", "Ask Copilot — get an answer in seconds")
    slide_num(sl, 3)

    add_rect(sl, 0.3, 1.4, 12.7, 1.0, BLUE_PALE, line=BLUE)
    add_text(sl, "Is Veritas InfoScale 8.0.2 compatible with RHEL 8 kernel 4.18.0-477.el8?",
             0.6, 1.55, 12.1, 0.6, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

    add_text(sl, "↓  Copilot searches vendor HCL + internet  ↓",
             0, 2.55, 13.33, 0.4, size=11, color=BLUE, align=PP_ALIGN.CENTER, italic=True)

    add_rect(sl, 0.3, 3.1, 12.7, 3.6, RGBColor(0xf8, 0xfa, 0xff), line=GREY)
    add_rect(sl, 0.3, 3.1, 12.7, 0.5, RED)
    add_text(sl, "❌  NOT COMPATIBLE", 0.5, 3.15, 12.3, 0.38,
             size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    content = [
        ("Reason:", "Supported range is 4.18.0-193.el8 → 4.18.0-425.el8. Kernel 4.18.0-477.el8 exceeds the upper bound."),
        ("References:", "1. Veritas HCL Oct 2023 — veritas.com/support — Section: Supported Kernels RHEL 8"),
        ("",            "2. Release Notes 8.0.2 — veritas.com/support — Known Limitations"),
        ("Confidence:", "High"),
        ("Patch note:", "Safe maximum is 4.18.0-425.el8. Do not patch beyond this."),
    ]
    for i, (label, val) in enumerate(content):
        if label:
            add_text(sl, label, 0.5, 3.75+i*0.46, 1.4, 0.4, size=10, bold=True, color=NAVY)
        add_text(sl, val, 1.9, 3.75+i*0.46, 11.0, 0.4, size=10, color=RGBColor(0x1f,0x29,0x37))


def slide_how_it_works(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    title_bar(sl, "How It Works", "Three files. No servers. No pipeline.")
    slide_num(sl, 4)

    nodes = [
        ("You ask\nCopilot Chat", BLUE,     0.3),
        ("copilot-\ninstructions.md", RGBColor(0x7c,0x3a,0xed), 3.1),
        ("sources/\n{app}.yaml",    RGBColor(0x08,0x91,0xb2), 5.9),
        ("Search\nHCL + Web",       GREEN,   8.7),
        ("Structured\nAnswer",      AMBER,   11.5),
    ]
    for label, col, x in nodes:
        add_rect(sl, x, 2.0, 1.5, 1.3, col)
        add_text(sl, label, x, 2.0, 1.5, 1.3, size=9, bold=True,
                 color=WHITE, align=PP_ALIGN.CENTER)
        if x < 11.5:
            add_text(sl, "→", x+1.5, 2.4, 1.6, 0.5, size=18, bold=True,
                     color=BLUE, align=PP_ALIGN.CENTER)

    captions = [
        ("plain\nEnglish",     0.3),
        ("how to\nanswer",     3.1),
        ("vendor\nURLs",       5.9),
        ("HCL +\ninternet",    8.7),
        ("verdict +\nrefs",   11.5),
    ]
    for cap, x in captions:
        add_text(sl, cap, x, 3.45, 1.5, 0.5, size=7.5, color=GREY, align=PP_ALIGN.CENTER, italic=True)

    boxes = [
        ("copilot-instructions.md", BLUE_PALE, BLUE,
         ["Tells Copilot exactly how to answer", "Defines answer format", "Sets confidence rules", "Handles edge cases"]),
        ("sources/{app}.yaml", RGBColor(0xe0,0xf2,0xfe), RGBColor(0x08,0x91,0xb2),
         ["Vendor HCL URLs", "Release notes URLs", "Search terms per app", "Supported versions list"]),
        ("Answer format", GREEN_PALE, GREEN,
         ["COMPATIBLE / NOT COMPATIBLE / UNKNOWN", "Exact version range", "Reference URLs + sections", "Confidence + patch note"]),
    ]
    for i, (title, bg, accent, items) in enumerate(boxes):
        x = 0.3 + i*4.35
        add_rect(sl, x, 4.2, 4.1, 2.9, bg, line=accent)
        add_rect(sl, x, 4.2, 4.1, 0.38, accent)
        add_text(sl, title, x+0.1, 4.23, 3.9, 0.32, size=9.5, bold=True,
                 color=WHITE, align=PP_ALIGN.CENTER)
        for j, item in enumerate(items):
            add_text(sl, f"• {item}", x+0.15, 4.68+j*0.48, 3.8, 0.42, size=9, color=NAVY)


def slide_sources(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    title_bar(sl, "Sources Structure", "Define once. Copilot uses them every time.")
    slide_num(sl, 5)

    add_text(sl, "Each application has a YAML file listing its official vendor docs and search terms. "
                 "Copilot reads these automatically when you ask about that app.",
             0.4, 1.4, 12.5, 0.5, size=11, color=NAVY)

    # code example
    add_rect(sl, 0.3, 2.0, 6.0, 4.9, RGBColor(0xf8,0xfa,0xff), line=GREY)
    add_rect(sl, 0.3, 2.0, 6.0, 0.35, NAVY)
    add_text(sl, "sources/veritas-infoscale.yaml", 0.45, 2.03, 5.7, 0.28,
             size=8.5, bold=True, color=WHITE)
    code_lines = [
        "app: veritas-infoscale",
        "versions: [8.0.2, 9.1]",
        "platforms: [rhel, ubuntu]",
        "",
        "docs:",
        "  - name: Veritas HCL",
        "    url: veritas.com/support/...",
        "    type: hcl",
        "",
        "  - name: Release Notes",
        "    url: veritas.com/support/...",
        "    type: release_notes",
        "",
        "search_terms:",
        "  - \"veritas infoscale {version}",
        "     rhel {platform_version}\"",
    ]
    for i, line in enumerate(code_lines):
        col = BLUE if line.startswith("app:") or line.startswith("docs:") or line.startswith("search") else RGBColor(0x1f,0x29,0x37)
        add_text(sl, line, 0.45, 2.45+i*0.28, 5.6, 0.28, size=8, color=col,
                 bold=line.startswith("app:") or line.startswith("docs:") or line.startswith("search"))

    # right side
    apps_now = [
        ("veritas-infoscale.yaml", "Veritas InfoScale 7.4 – 9.1",   BLUE),
        ("oracle-db.yaml",         "Oracle Database 19c, 21c, 23ai", RGBColor(0x08,0x91,0xb2)),
        ("sap-hana.yaml",          "SAP HANA 2.0 SPS06–08",         RGBColor(0x7c,0x3a,0xed)),
    ]
    add_text(sl, "Included today:", 6.6, 2.0, 6.4, 0.4, size=11, bold=True, color=NAVY)
    for i, (fname, label, col) in enumerate(apps_now):
        add_rect(sl, 6.6, 2.45+i*0.62, 6.4, 0.52, BLUE_PALE, line=col)
        add_text(sl, fname, 6.75, 2.5+i*0.62, 3.0, 0.4, size=8.5, bold=True, color=col)
        add_text(sl, label, 9.8,  2.5+i*0.62, 3.1, 0.4, size=8.5, color=NAVY)

    add_rect(sl, 6.6, 4.45, 6.4, 0.6, GREEN_PALE, line=GREEN)
    add_text(sl, "➕  Adding a new app = one YAML file, < 5 minutes",
             6.75, 4.55, 6.1, 0.4, size=10, bold=True, color=GREEN)

    add_rect(sl, 6.6, 5.2, 6.4, 1.65, AMBER_PALE, line=AMBER)
    add_text(sl, "You can also provide:", 6.75, 5.28, 6.1, 0.35, size=10, bold=True, color=AMBER)
    for i, b in enumerate(["Specific doc URLs you already trust", "Internal KB article links", "Vendor portal search terms"]):
        add_text(sl, f"• {b}", 6.75, 5.65+i*0.38, 6.1, 0.35, size=9.5, color=NAVY)


def slide_future(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    title_bar(sl, "Future: LLM API Integration", "Same structure. Automated backend.")
    slide_num(sl, 6)

    add_text(sl, "The PoC is built so that plugging in an LLM API requires zero structural changes.",
             0.4, 1.4, 12.5, 0.4, size=12, color=NAVY)

    phases = [
        ("Phase 1 — Now (PoC)",          BLUE,  BLUE_PALE,
         ["VS Code Copilot Chat", "Manual question → instant answer", "No API key needed", "Sources guide Copilot"]),
        ("Phase 2 — LLM API",             GREEN, GREEN_PALE,
         ["Same sources/ files", "Script calls OpenAI / Anthropic / Azure", "Fully automated", "One env var to switch"]),
        ("Phase 3 — UI / Integration",    AMBER, AMBER_PALE,
         ["Web UI or CLI for wider teams", "Patch tool integration", "Bulk compatibility checks", "Audit trail"]),
    ]
    for i, (title, accent, bg, items) in enumerate(phases):
        x = 0.3 + i*4.35
        add_rect(sl, x, 2.0, 4.1, 4.9, bg, line=accent)
        add_rect(sl, x, 2.0, 4.1, 0.42, accent)
        add_text(sl, title, x+0.1, 2.05, 3.9, 0.32, size=9.5, bold=True,
                 color=WHITE, align=PP_ALIGN.CENTER)
        for j, item in enumerate(items):
            add_text(sl, f"• {item}", x+0.2, 2.6+j*0.58, 3.7, 0.5, size=10, color=NAVY)

    add_rect(sl, 0.3, 7.05, 12.7, 0.3, NAVY)
    add_text(sl, "sources/ files  ·  copilot-instructions  ·  answer format  — stay exactly the same across all phases",
             0.4, 7.07, 12.5, 0.25, size=8.5, color=WHITE, align=PP_ALIGN.CENTER, italic=True)


def slide_summary(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    slide_bg(sl, NAVY)
    add_rect(sl, 0, 0, 13.33, 0.06, BLUE)
    add_rect(sl, 0, 7.44, 13.33, 0.06, BLUE)

    add_text(sl, "Summary", 0.5, 0.4, 12.3, 0.8, size=32, bold=True,
             color=WHITE, align=PP_ALIGN.CENTER)

    points = [
        ("The problem",  "30–60 min of manual research before every patch window",          RED),
        ("The solution", "Ask Copilot, get a structured answer with references in seconds", GREEN),
        ("The core",     "copilot-instructions.md + sources/{app}.yaml — that's it",        BLUE_LIGHT),
        ("Adding apps",  "One YAML file per application, < 5 minutes",                      AMBER),
        ("Future-ready", "LLM API plugs in with one env var — zero structural changes",      GREEN),
    ]
    for i, (label, text, col) in enumerate(points):
        y = 1.4 + i * 1.06
        add_rect(sl, 0.4, y, 1.3, 0.72, col)
        add_text(sl, label, 0.4, y, 1.3, 0.72, size=9, bold=True,
                 color=NAVY, align=PP_ALIGN.CENTER)
        add_rect(sl, 1.75, y, 11.2, 0.72, RGBColor(0x16,0x2a,0x55))
        add_text(sl, text, 1.9, y+0.1, 10.9, 0.52, size=11, color=WHITE)

    slide_num(sl, 7)


# ── Main ──────────────────────────────────────────────────────────────────────
def build(out: Path):
    prs = Presentation()
    prs.slide_width  = SW
    prs.slide_height = SH

    slide_cover(prs)
    slide_problem(prs)
    slide_solution(prs)
    slide_how_it_works(prs)
    slide_sources(prs)
    slide_future(prs)
    slide_summary(prs)

    prs.save(str(out))
    print(f"Presentation → {out}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/presentation.pptx")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
