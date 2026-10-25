import os
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import io
import re
import html
import json

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    HRFlowable,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
)
from auth import require_beta_access, track_usage_event, get_supabase

# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

def get_setting(name, default=None):
    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


OPENAI_API_KEY = get_setting("OPENAI_API_KEY")
OPENAI_MODEL = get_setting("OPENAI_MODEL", "gpt-5.6-terra")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

st.set_page_config(
    page_title="Venture Navigator AI",
    page_icon="VN_Icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)



# =========================================================
# BRANDED PDF REPORT
# =========================================================
def build_branded_pdf(
    report_text,
    company_name=None,
    executive_data=None,
    currency_code="ZAR",
    venture_stage=None,
    geography=None,
):
    """Create the premium Venture Navigator PDF deliverable.

    The human-readable research report remains the source of detail. The structured
    executive block is used only to create concise decision-support cards at the
    front of the document.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=13 * mm,
        bottomMargin=17 * mm,
        title="Venture Navigator - Venture Intelligence Report",
        author="AI Catalyst Studio",
    )

    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#123d59")
    CYAN = colors.HexColor("#14b9d6")
    BLUE = colors.HexColor("#168fbe")
    GRAPHITE = colors.HexColor("#263c49")
    MUTED = colors.HexColor("#607986")
    SILVER = colors.HexColor("#d9dee2")
    SILVER_LIGHT = colors.HexColor("#eef1f3")
    SILVER_PALE = colors.HexColor("#f4f6f7")
    BORDER = colors.HexColor("#bfc7cc")

    title_style = ParagraphStyle(
        "VNTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "VNSubtitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=13, textColor=BLUE, alignment=TA_CENTER, spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "VNMeta", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.8, leading=12, textColor=MUTED, alignment=TA_CENTER, spaceAfter=3,
    )
    section_style = ParagraphStyle(
        "VNSection", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=15.5, leading=19, textColor=NAVY, spaceBefore=11, spaceAfter=7,
    )
    h2_style = ParagraphStyle(
        "VNH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12.5, leading=16, textColor=colors.HexColor("#176c91"),
        spaceBefore=8, spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "VNBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.2, leading=13.6, textColor=GRAPHITE, spaceAfter=5,
    )
    small_style = ParagraphStyle(
        "VNSmall", parent=body_style, fontSize=8, leading=11, textColor=MUTED,
    )
    bullet_style = ParagraphStyle(
        "VNBullet", parent=body_style, leftIndent=12, firstLineIndent=-7, spaceAfter=3.5,
    )
    card_label = ParagraphStyle(
        "VNCardLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.4, leading=9, textColor=MUTED, alignment=TA_CENTER,
    )
    card_value = ParagraphStyle(
        "VNCardValue", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=13, leading=15, textColor=NAVY, alignment=TA_CENTER,
    )
    callout_title = ParagraphStyle(
        "VNCalloutTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=12, textColor=NAVY,
    )
    callout_body = ParagraphStyle(
        "VNCalloutBody", parent=body_style, fontSize=8.8, leading=12.5,
    )
    table_header = ParagraphStyle(
        "VNTableHeader", parent=small_style, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    table_body = ParagraphStyle(
        "VNTableBody", parent=small_style, fontSize=7.6, leading=10.3, textColor=GRAPHITE,
    )

    story = []

    # Venture Navigator product logo
    vn_logo = Path("VN_Logo_Horizontal.png")
    if vn_logo.exists():
        img = RLImage(str(vn_logo))
        max_width = 175 * mm
        max_height = 30 * mm
        scale = min(max_width / img.imageWidth, max_height / img.imageHeight, 1)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        story.append(img)
        story.append(Spacer(1, 2 * mm))

    # AI Catalyst Studio parent-company logo beneath
    company_logo_candidates = [
        Path("Elongated_Logo_Header.png"),
        Path("Elongated_Logo.png"),
        Path("New_Logo_250626.png"),
    ]
    company_logo = next((p for p in company_logo_candidates if p.exists()), None)

    if company_logo:
        img = RLImage(str(company_logo))
        max_width = 150 * mm
        max_height = 18 * mm
        scale = min(max_width / img.imageWidth, max_height / img.imageHeight, 1)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        story.append(img)
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Venture Navigator", title_style))
    story.append(Paragraph("Venture Intelligence Report", subtitle_style))

    meta_bits = []
    if company_name:
        meta_bits.append(html.escape(company_name))
    if venture_stage:
        meta_bits.append(f"Stage: {html.escape(str(venture_stage))}")
    if geography:
        meta_bits.append(f"Geography: {html.escape(str(geography))}")
    meta_bits.append(datetime.now().strftime("%d %B %Y"))
    story.append(Paragraph(" &nbsp; | &nbsp; ".join(meta_bits), meta_style))
    story.append(HRFlowable(width="100%", thickness=1.1, color=CYAN, spaceBefore=3, spaceAfter=8))

    def fmt_inline(value):
        value = str(value or "")
        # Keep citations clickable while displaying the source label rather than a long URL.
        links = []
        def stash_link(match):
            label, url = match.group(1), match.group(2)
            token = f"__VNLINK{len(links)}__"
            links.append((token, label, url))
            return token
        value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", stash_link, value)
        safe = html.escape(value)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        safe = re.sub(r"\*(.+?)\*", r"<i>\1</i>", safe)
        for token, label, url in links:
            safe = safe.replace(
                token,
                f'<link href="{html.escape(url, quote=True)}" color="#176c91"><u>{html.escape(label)}</u></link>'
            )
        return safe

    def metric_card(label, value):
        return [Paragraph(label, card_label), Spacer(1, 1.2 * mm), Paragraph(value, card_value)]

    def score(value):
        return clamp_score(value)

    # ------------------------------------------------------------------
    # EXECUTIVE INTELLIGENCE DASHBOARD
    # ------------------------------------------------------------------
    if executive_data:
        story.append(Paragraph("Executive Intelligence Dashboard", section_style))
        story.append(Paragraph(
            "Directional decision-support indicators derived from the supplied venture evidence and current market analysis. Scores are not guarantees.",
            small_style,
        ))
        story.append(Spacer(1, 2 * mm))

        metrics = [
            metric_card("OPPORTUNITY SCORE", f"{score(executive_data.get('opportunity_score'))}/100"),
            metric_card("MARKET ATTRACTIVENESS", html.escape(str(executive_data.get('market_attractiveness', 'Not assessed')))),
            metric_card("DIFFERENTIATION", f"{score(executive_data.get('differentiation_score'))}/100"),
            metric_card("INVESTOR READINESS", f"{score(executive_data.get('investor_readiness_score'))}/100"),
        ]
        metric_table = Table([metrics], colWidths=[43 * mm] * 4, rowHeights=[25 * mm])
        metric_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SILVER_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#ccd3d8")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(metric_table)
        story.append(Paragraph(
            "Opportunity Score combines customer pain, market accessibility, differentiation potential, MVP feasibility and revenue potential.",
            small_style,
        ))
        story.append(Spacer(1, 4 * mm))

        val = executive_data.get("valuation") or {}
        val_status = str(val.get("status", "Not assessed"))
        low, high = val.get("low"), val.get("high")
        if val_status.lower() == "available" and low is not None and high is not None:
            try:
                val_display = f"{currency_code} {float(low):,.0f} - {currency_code} {float(high):,.0f}"
            except Exception:
                val_display = "Valuation range unavailable"
        else:
            val_display = "Insufficient evidence for a responsible monetary range"

        valuation_box = Table([
            [Paragraph("INDICATIVE VENTURE VALUATION", callout_title), Paragraph(fmt_inline(val_display), callout_body)],
            [Paragraph("Method / confidence", small_style), Paragraph(fmt_inline(f"{val.get('method','Not assessed')} | {val.get('confidence','Low')} confidence"), small_style)],
        ], colWidths=[53 * mm, 119 * mm])
        valuation_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SILVER_PALE),
            ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(valuation_box)
        story.append(Paragraph(
            "Indicative decision-support estimate only - not a formal business valuation, investment opinion or fairness opinion.",
            small_style,
        ))

        evidence = executive_data.get("evidence_quality") or {}
        if isinstance(evidence, dict) and evidence:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("Evidence Quality", h2_style))
            evidence_rows = [
                [Paragraph("Overall", callout_title), Paragraph(fmt_inline(evidence.get("overall", "Not assessed")), callout_body)],
                [Paragraph("Verified market evidence", callout_title), Paragraph(fmt_inline(evidence.get("verified_market_evidence", "Not assessed")), callout_body)],
                [Paragraph("User-supplied evidence", callout_title), Paragraph(fmt_inline(evidence.get("user_supplied_evidence", "Not assessed")), callout_body)],
                [Paragraph("Assumption load", callout_title), Paragraph(fmt_inline(evidence.get("assumption_load", "Not assessed")), callout_body)],
            ]
            if evidence.get("summary"):
                evidence_rows.append([Paragraph("Summary", callout_title), Paragraph(fmt_inline(evidence.get("summary")), callout_body)])
            evidence_table = Table(evidence_rows, colWidths=[53 * mm, 119 * mm])
            evidence_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SILVER_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d3d9dd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(evidence_table)

        next_action = executive_data.get("recommended_next_action")
        if next_action:
            story.append(Spacer(1, 3 * mm))
            action_box = Table([[Paragraph("RECOMMENDED NEXT ACTION", callout_title), Paragraph(fmt_inline(next_action), callout_body)]], colWidths=[53 * mm, 119 * mm])
            action_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f6f9")),
                ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(action_box)

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Decision Stress Test", h2_style))
        challenge = executive_data.get("challenge") or {}
        what_not = executive_data.get("what_not_to_build") or []
        rows = []
        if isinstance(challenge, dict):
            if challenge.get("why_it_may_fail"):
                rows.append([Paragraph("Why it may fail", callout_title), Paragraph(fmt_inline(challenge.get("why_it_may_fail")), callout_body)])
            if challenge.get("key_assumption"):
                rows.append([Paragraph("Key assumption", callout_title), Paragraph(fmt_inline(challenge.get("key_assumption")), callout_body)])
            if challenge.get("what_would_change_the_conclusion"):
                rows.append([Paragraph("What would change the conclusion", callout_title), Paragraph(fmt_inline(challenge.get("what_would_change_the_conclusion")), callout_body)])
        if rows:
            challenge_table = Table(rows, colWidths=[53 * mm, 119 * mm])
            challenge_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SILVER_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d3d9dd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(challenge_table)

        if what_not:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("What Not to Build Yet", h2_style))
            for item in what_not[:5]:
                if isinstance(item, dict):
                    label = item.get("item", "Option")
                    reason = item.get("reason", "")
                    story.append(Paragraph(f"• <b>{fmt_inline(label)}</b> - {fmt_inline(reason)}", bullet_style))
                else:
                    story.append(Paragraph("• " + fmt_inline(item), bullet_style))

        plan = executive_data.get("action_plan_90_day") or {}
        if isinstance(plan, dict) and plan:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("30 / 60 / 90-Day Action Plan", h2_style))
            plan_cells = []
            for key, title in [("days_0_30", "0-30 DAYS"), ("days_31_60", "31-60 DAYS"), ("days_61_90", "61-90 DAYS")]:
                items = plan.get(key) or []
                body = "<br/>".join([f"• {fmt_inline(x)}" for x in items[:5]]) or "No action returned."
                plan_cells.append([Paragraph(title, card_label), Spacer(1, 1.5 * mm), Paragraph(body, small_style)])
            plan_table = Table([plan_cells], colWidths=[57.3 * mm] * 3)
            plan_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SILVER_PALE),
                ("BOX", (0, 0), (-1, -1), 0.65, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d3d9dd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(plan_table)

        story.append(PageBreak())

    story.append(Paragraph("Detailed Venture Intelligence", section_style))

    # ------------------------------------------------------------------
    # HUMAN-READABLE REPORT, INCLUDING MARKDOWN TABLES
    # ------------------------------------------------------------------
    lines = report_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line or line == "---":
            if not line:
                story.append(Spacer(1, 2 * mm))
            i += 1
            continue

        # Markdown tables -> real PDF tables.
        if line.startswith("|") and line.endswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) >= 2:
                raw_rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
                # Skip markdown separator row.
                raw_rows = [r for idx, r in enumerate(raw_rows) if idx != 1 or not all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in r)]
                if raw_rows:
                    ncols = max(len(r) for r in raw_rows)
                    rows = []
                    for ridx, r in enumerate(raw_rows):
                        r = r + [""] * (ncols - len(r))
                        style = table_header if ridx == 0 else table_body
                        rows.append([Paragraph(fmt_inline(c), style) for c in r])
                    widths = [172 * mm / ncols] * ncols
                    t = Table(rows, colWidths=widths, repeatRows=1)
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("BACKGROUND", (0, 1), (-1, -1), SILVER_PALE),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SILVER_PALE, SILVER_LIGHT]),
                        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 3 * mm))
                    continue

        if line.startswith("### "):
            story.append(Paragraph(fmt_inline(line[4:]), h2_style)); i += 1; continue
        if line.startswith("## "):
            story.append(Paragraph(fmt_inline(line[3:]), section_style)); i += 1; continue
        if line.startswith("# "):
            story.append(Paragraph(fmt_inline(line[2:]), section_style)); i += 1; continue
        if line.startswith(("- ", "* ", "• ")):
            content = line[2:] if line[:2] in ("- ", "* ") else line[1:].strip()
            story.append(Paragraph("• " + fmt_inline(content), bullet_style)); i += 1; continue
        numbered = re.match(r"^(\d+)\.\s+(.*)", line)
        if numbered:
            story.append(Paragraph(f"{numbered.group(1)}. " + fmt_inline(numbered.group(2)), bullet_style)); i += 1; continue
        if line.startswith("> "):
            q = Table([[Paragraph(fmt_inline(line[2:]), callout_body)]], colWidths=[172 * mm])
            q.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f6f9")),
                ("LINEBEFORE", (0, 0), (0, -1), 3, CYAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(q); story.append(Spacer(1, 2 * mm)); i += 1; continue

        story.append(Paragraph(fmt_inline(line), body_style))
        i += 1

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.7, color=BORDER, spaceBefore=3, spaceAfter=5))
    story.append(Paragraph(
        "Generated by Venture Navigator - AI Catalyst Studio<br/>"
        '<link href="https://venture.aicatalyststudio.co.za" color="#176c91">venture.aicatalyststudio.co.za</link><br/>'
        "Your venture. Your data. Your intellectual property.",
        ParagraphStyle("VNFooter", parent=styles["Normal"], fontSize=7.8, leading=10.5, alignment=TA_CENTER, textColor=MUTED),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# FINAL RESTORED THEME
# Metallic silver + navy + cyan
# =========================================================

st.markdown("""
<style>

/* -------------------------------------------------------
   GLOBAL METALLIC SILVER BACKGROUND
------------------------------------------------------- */

html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
.stMain,
section.main {

    background:
        radial-gradient(
            circle at 12% 8%,
            rgba(255,255,255,0.88),
            transparent 20%
        ),
        radial-gradient(
            circle at 88% 14%,
            rgba(255,255,255,0.42),
            transparent 22%
        ),
        linear-gradient(
            135deg,
            #fdfefe 0%,
            #d5dce2 10%,
            #f6f8fa 18%,
            #b8c1c9 28%,
            #eef2f5 38%,
            #aeb7c0 50%,
            #f7f9fb 61%,
            #c5cdd5 73%,
            #edf1f4 84%,
            #a9b2bb 92%,
            #fdfefe 100%
        ) !important;

    background-attachment: fixed !important;
}

[data-testid="stMainBlockContainer"],
.block-container {
    background: transparent !important;
}

.block-container {
    max-width: 1260px;
    padding-top: 1.35rem;
    padding-bottom: 4rem;
}


/* -------------------------------------------------------
   STREAMLIT CHROME
------------------------------------------------------- */

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: #0b3147 !important;
    border-bottom: 1px solid rgba(29, 189, 218, 0.26);
}


/* -------------------------------------------------------
   DEFAULT TYPOGRAPHY
------------------------------------------------------- */

h1,
h2,
h3 {
    color: #153b55 !important;
}

p,
li {
    color: #2d4e64;
}

strong {
    color: #183d55;
}


/* -------------------------------------------------------
   HERO PANEL
------------------------------------------------------- */

.hero-panel {
    background:
        linear-gradient(
            135deg,
            rgba(247,250,252,0.80),
            rgba(202,211,219,0.84)
        );

    border: 1px solid rgba(55, 78, 94, 0.23);
    border-radius: 8px;

    padding: 1.3rem 1.4rem;
    margin-bottom: 1.5rem;

    box-shadow:
        0 12px 30px rgba(64, 78, 88, 0.10);
}


/* -------------------------------------------------------
   BORDERED CONTAINERS
------------------------------------------------------- */

div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(63, 85, 101, 0.22) !important;
    border-radius: 10px !important;

    box-shadow:
        0 10px 28px rgba(68, 82, 94, 0.12);
}


/* -------------------------------------------------------
   INFO BADGES
------------------------------------------------------- */

div[data-testid="stAlert"] {
    background:
        linear-gradient(
            135deg,
            #104c70 0%,
            #185d86 100%
        ) !important;

    border:
        1px solid rgba(24, 203, 226, 0.38) !important;

    border-radius: 13px !important;

    box-shadow:
        0 8px 18px rgba(18, 70, 100, 0.18);
}

div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span,
div[data-testid="stAlert"] strong {
    color: #ffffff !important;
    font-weight: 700 !important;
}


/* -------------------------------------------------------
   INTELLIGENCE ENGINE PANEL
------------------------------------------------------- */

.st-key-intelligence_engine {
    background:
        linear-gradient(
            135deg,
            rgba(239,243,246,0.94),
            rgba(211,219,225,0.94)
        ) !important;

    border:
        1px solid rgba(61, 84, 100, 0.22) !important;

    border-radius:
        10px !important;

    box-shadow:
        0 10px 28px rgba(70, 85, 96, 0.10);
}

.st-key-intelligence_engine h1,
.st-key-intelligence_engine h2,
.st-key-intelligence_engine h3,
.st-key-intelligence_engine p,
.st-key-intelligence_engine span,
.st-key-intelligence_engine strong {
    color: #153b55 !important;
}


/* -------------------------------------------------------
   FOUR LIGHT STRATEGY CARDS
------------------------------------------------------- */

.st-key-card_understand,
.st-key-card_discover,
.st-key-card_differentiate,
.st-key-card_navigate {

    min-height: 220px !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;

    background:
        linear-gradient(
            145deg,
            rgba(216,222,227,0.98) 0%,
            rgba(241,244,246,0.98) 48%,
            rgba(198,206,213,0.98) 100%
        ) !important;

    border:
        1px solid rgba(32, 113, 145, 0.22) !important;

    border-radius:
        14px !important;

    box-shadow:
        0 10px 24px rgba(45, 66, 80, 0.10) !important;
}

.st-key-card_understand h1,
.st-key-card_understand h2,
.st-key-card_understand h3,
.st-key-card_understand p,
.st-key-card_understand span,
.st-key-card_understand strong,

.st-key-card_discover h1,
.st-key-card_discover h2,
.st-key-card_discover h3,
.st-key-card_discover p,
.st-key-card_discover span,
.st-key-card_discover strong,

.st-key-card_differentiate h1,
.st-key-card_differentiate h2,
.st-key-card_differentiate h3,
.st-key-card_differentiate p,
.st-key-card_differentiate span,
.st-key-card_differentiate strong,

.st-key-card_navigate h1,
.st-key-card_navigate h2,
.st-key-card_navigate h3,
.st-key-card_navigate p,
.st-key-card_navigate span,
.st-key-card_navigate strong {

    color:
        #153b55 !important;
}

.st-key-card_understand [data-testid="stCaptionContainer"] p,
.st-key-card_discover [data-testid="stCaptionContainer"] p,
.st-key-card_differentiate [data-testid="stCaptionContainer"] p,
.st-key-card_navigate [data-testid="stCaptionContainer"] p {

    color:
        #109fc3 !important;

    font-weight:
        850 !important;
}



.st-key-card_understand div[data-testid="stVerticalBlockBorderWrapper"],
.st-key-card_discover div[data-testid="stVerticalBlockBorderWrapper"],
.st-key-card_differentiate div[data-testid="stVerticalBlockBorderWrapper"],
.st-key-card_navigate div[data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 220px !important;
    height: 100% !important;
}

.st-key-card_understand h3,
.st-key-card_discover h3,
.st-key-card_differentiate h3,
.st-key-card_navigate h3 {
    margin-top: 0.35rem !important;
    margin-bottom: 0.7rem !important;
}

.st-key-card_understand p:not([data-testid]),
.st-key-card_discover p:not([data-testid]),
.st-key-card_differentiate p:not([data-testid]),
.st-key-card_navigate p:not([data-testid]) {
    line-height: 1.55 !important;
}

/* -------------------------------------------------------
   CAPTIONS
------------------------------------------------------- */

div[data-testid="stCaptionContainer"] p {
    color: #526f80 !important;
    font-weight: 720 !important;
}


/* -------------------------------------------------------
   PRIVACY / TRUST PANEL
------------------------------------------------------- */

.vn-trust-panel {
    background: linear-gradient(135deg, rgba(218,224,229,0.98), rgba(241,244,246,0.98), rgba(201,210,216,0.98));
    border: 1px solid rgba(19, 153, 188, 0.28);
    border-left: 4px solid #20b9d7;
    border-radius: 14px;
    padding: 1rem 1.15rem;
    margin: 0.85rem 0 1.15rem 0;
    box-shadow: 0 8px 20px rgba(39, 67, 82, 0.08);
}
.vn-trust-title {
    color: #153b55 !important;
    font-size: 1.02rem;
    font-weight: 850;
    margin-bottom: 0.25rem;
}
.vn-trust-copy {
    color: #35576a !important;
    font-size: 0.94rem;
    line-height: 1.5;
    margin: 0;
}

/* -------------------------------------------------------
   VENTURE PROFILE TITLE
------------------------------------------------------- */

.venture-profile-title {
    color: #153b55 !important;
    font-size: 2.35rem;
    font-weight: 850;
    letter-spacing: -0.025em;
    margin-top: 1rem;
    margin-bottom: 0.55rem;
}


/* -------------------------------------------------------
   VENTURE PROFILE FORM
------------------------------------------------------- */

div[data-testid="stForm"] {

    background:
        linear-gradient(
            145deg,
            rgba(211,218,224,0.98) 0%,
            rgba(239,242,244,0.98) 48%,
            rgba(195,203,210,0.98) 100%
        ) !important;

    border:
        1px solid rgba(42, 105, 133, 0.22) !important;

    border-radius:
        18px !important;

    padding:
        1.65rem !important;

    box-shadow:
        0 14px 34px rgba(38, 64, 80, 0.12);
}


/* -------------------------------------------------------
   FORM LABELS
------------------------------------------------------- */

label,
div[data-testid="stWidgetLabel"] p {
    color: #173d52 !important;
    font-weight: 740 !important;
}


/* -------------------------------------------------------
   INPUT FIELDS
------------------------------------------------------- */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {

    background:
        #f3f9fc !important;

    border:
        1px solid #9edfeb !important;

    border-radius:
        11px !important;
}

input,
textarea {

    color:
        #173d52 !important;

    -webkit-text-fill-color:
        #173d52 !important;

    font-weight:
        550 !important;
}

input::placeholder,
textarea::placeholder {

    color:
        #66889c !important;

    -webkit-text-fill-color:
        #66889c !important;

    opacity:
        1 !important;
}

div[data-baseweb="select"] span {
    color: #173d52 !important;
}


/* -------------------------------------------------------
   PRIMARY BUTTON
------------------------------------------------------- */

.stFormSubmitButton button {

    min-height:
        3.35rem !important;

    border:
        1px solid rgba(255,255,255,0.35) !important;

    border-radius:
        11px !important;

    background:
        linear-gradient(
            95deg,
            #29cedc 0%,
            #159ed6 45%,
            #3276e3 100%
        ) !important;

    box-shadow:
        0 10px 25px rgba(21, 111, 190, 0.28) !important;

    color:
        #ffffff !important;

    font-weight:
        820 !important;
}

.stFormSubmitButton button p,
.stFormSubmitButton button span {
    color: #ffffff !important;
}


/* -------------------------------------------------------
   DOWNLOAD BUTTON
------------------------------------------------------- */

.stDownloadButton button {

    width:
        100%;

    min-height:
        3rem;

    background:
        linear-gradient(
            90deg,
            #0d4968,
            #166d92
        ) !important;

    border:
        1px solid #24bad3 !important;

    color:
        #ffffff !important;

    border-radius:
        10px !important;
}


/* -------------------------------------------------------
   STATUS PANEL
------------------------------------------------------- */

div[data-testid="stStatusWidget"] {

    background:
        #0d3044 !important;

    border:
        1px solid rgba(24, 201, 224, 0.30) !important;

    border-radius:
        15px !important;
}

div[data-testid="stStatusWidget"] p,
div[data-testid="stStatusWidget"] span {
    color: #ffffff !important;
}


/* -------------------------------------------------------
   LOGO
------------------------------------------------------- */

div[data-testid="stImage"] img {

    border-radius:
        14px;

    border:
        1px solid rgba(22, 191, 218, 0.28);

    box-shadow:
        0 10px 24px rgba(38, 61, 75, 0.18);
}


/* -------------------------------------------------------
   DIVIDER
------------------------------------------------------- */

hr {
    border-color: rgba(48, 77, 97, 0.18) !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# REGISTRATION + BETA ACCESS
# =========================================================

beta_access = require_beta_access()


# =========================================================
# AI CATALYST STUDIO WEBSITE HEADER
# =========================================================
if os.path.exists("Elongated_Logo_Header.png"):
    top_logo_left, top_logo_mid, top_logo_right = st.columns(
        [1.2, 5.6, 1.2]
    )

    with top_logo_mid:
        st.image(
            "VN_Logo_Horizontal.png",
            use_container_width=True
        )

    st.write("")



# =========================================================
# ADMIN BETA STATS BOARD
# =========================================================
if beta_access.get("is_admin"):

    with st.expander(
        "📊 Venture Navigator Beta Stats",
        expanded=False
    ):
        try:
            supabase = get_supabase()

            users_response = (
                supabase
                .table("venture_beta_users")
                .select("*")
                .order("registered_at", desc=True)
                .execute()
            )

            events_response = (
                supabase
                .table("venture_usage_events")
                .select("*")
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )

            users = users_response.data or []
            events = events_response.data or []

            now = datetime.now(timezone.utc)

            report_events = [
                e for e in events
                if e.get("event_type") == "report_generated"
            ]

            login_events = [
                e for e in events
                if e.get("event_type") == "login"
            ]

            active_24h = set()
            active_7d = set()

            for event in events:
                created = event.get("created_at")
                if not created:
                    continue

                try:
                    dt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )

                    if now - dt <= timedelta(hours=24):
                        active_24h.add(event.get("user_id"))

                    if now - dt <= timedelta(days=7):
                        active_7d.add(event.get("user_id"))

                except Exception:
                    pass

            active_trials = 0
            expired_trials = 0

            for user in users:
                registered = user.get("registered_at")

                if not registered:
                    continue

                try:
                    created = datetime.fromisoformat(
                        registered.replace("Z", "+00:00")
                    )

                    if created + timedelta(days=7) > now:
                        active_trials += 1
                    else:
                        expired_trials += 1

                except Exception:
                    pass

            st.markdown("### Venture Navigator Beta Control Room")

            m1, m2, m3, m4, m5 = st.columns(5)

            m1.metric(
                "Registered Users",
                len(users)
            )

            m2.metric(
                "Active Today",
                len(active_24h)
            )

            m3.metric(
                "Active 7 Days",
                len(active_7d)
            )

            m4.metric(
                "Reports Generated",
                len(report_events)
            )

            m5.metric(
                "Beta Access",
                "Open"
            )

            st.divider()

            # -------------------------------------------------
            # DAILY REPORT USAGE
            # -------------------------------------------------
            daily_usage = {}

            for event in report_events:
                created = event.get("created_at")

                if not created:
                    continue

                try:
                    dt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )

                    day = dt.strftime("%Y-%m-%d")

                    daily_usage[day] = (
                        daily_usage.get(day, 0) + 1
                    )

                except Exception:
                    pass

            left, right = st.columns([1.25, 1])

            with left:
                st.markdown("#### Daily Report Usage")

                if daily_usage:
                    chart_df = pd.DataFrame(
                        [
                            {
                                "Date": day,
                                "Reports": count
                            }
                            for day, count
                            in sorted(daily_usage.items())
                        ]
                    ).set_index("Date")

                    st.bar_chart(chart_df)
                else:
                    st.info(
                        "No report-generation activity recorded yet."
                    )

            # -------------------------------------------------
            # MOST ACTIVE USERS
            # -------------------------------------------------
            with right:
                st.markdown("#### Most Active Users")

                usage_by_user = {}

                for event in report_events:
                    email = (
                        event.get("user_email")
                        or "Unknown user"
                    )

                    usage_by_user[email] = (
                        usage_by_user.get(email, 0) + 1
                    )

                if usage_by_user:
                    active_df = pd.DataFrame(
                        [
                            {
                                "User": email,
                                "Reports": count
                            }
                            for email, count in sorted(
                                usage_by_user.items(),
                                key=lambda x: x[1],
                                reverse=True
                            )
                        ]
                    )

                    st.dataframe(
                        active_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info(
                        "No user report activity yet."
                    )

            st.divider()

            # -------------------------------------------------
            # USER STATUS
            # -------------------------------------------------
            st.markdown("#### Beta Users")

            user_rows = []

            for user in users:
                registered = user.get("registered_at")
                last_login = user.get("last_login_at")


                user_report_count = sum(
                    1
                    for event in report_events
                    if event.get("user_id") == user.get("user_id")
                )

                user_rows.append(
                    {
                        "Email": user.get("email"),
                        "Registered": registered,
                        "Last Login": last_login,"Reports": user_report_count,
                    }
                )

            if user_rows:
                st.dataframe(
                    pd.DataFrame(user_rows),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No beta users recorded yet.")

            st.divider()

            # -------------------------------------------------
            # RECENT ACTIVITY
            # -------------------------------------------------
            st.markdown("#### Recent Activity")

            recent_rows = []

            for event in events[:30]:
                recent_rows.append(
                    {
                        "Time": event.get("created_at"),
                        "User": event.get("user_email"),
                        "Event": event.get("event_type"),
                        "Venture": event.get("venture_name"),
                        "Stage": event.get("venture_stage"),
                        "Primary Goal": event.get("primary_goal"),
                    }
                )

            if recent_rows:
                st.dataframe(
                    pd.DataFrame(recent_rows),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "No usage events have been recorded yet."
                )

            st.caption(
                f"Login events recorded: {len(login_events)}"
            )

        except Exception as stats_error:
            st.warning(
                f"Stats board could not be loaded: {stats_error}"
            )



# =========================================================
# HERO
# =========================================================

logo_path = "New_Logo_250626.png"

with st.container(border=True):

    logo_col, title_col = st.columns(
        [1.15, 5],
        vertical_alignment="center"
    )

    with logo_col:

        if os.path.exists(logo_path):
            st.image(
                logo_path,
                use_container_width=True
            )

        else:
            st.markdown("### AI Catalyst Studio")

    with title_col:

        st.caption(
            "AI CATALYST STUDIO • BUSINESS INTELLIGENCE"
        )

        st.title(
            "Venture Navigator AI"
        )

        st.markdown(
            """
            ### Turn business ideas into commercial intelligence.

            Analyse the **market**, **competition**, **opportunity gaps**,
            **differentiation**, **MVP direction** and practical actions
            required to move a venture forward.
            """
        )

        b1, b2, b3, b4 = st.columns(4)

        b1.info("📊 Market Intelligence")
        b2.info("🎯 Opportunity Discovery")
        b3.info("💡 Differentiation")
        b4.info("🚀 MVP Strategy")

st.write("")

# =========================================================
# INTELLIGENCE ENGINE
# =========================================================

with st.container(
    border=True,
    key="intelligence_engine"
):

    st.caption(
        "VENTURE INTELLIGENCE ENGINE"
    )

    st.markdown(
        """
        ### Business → Market → Competitors → Opportunity Gaps → Differentiation → MVP → Action Plan
        """
    )

st.write("")

# =========================================================
# FOUR VALUE CARDS
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    with st.container(
        border=True,
        key="card_understand"
    ):

        st.caption("01")
        st.subheader("Understand")

        st.markdown(
            "Clarify the **venture, customer, problem** and commercial proposition."
        )


with c2:

    with st.container(
        border=True,
        key="card_discover"
    ):

        st.caption("02")
        st.subheader("Discover")

        st.markdown(
            "Identify **competitors, alternatives** and underserved opportunities."
        )


with c3:

    with st.container(
        border=True,
        key="card_differentiate"
    ):

        st.caption("03")
        st.subheader("Differentiate")

        st.markdown(
            "Find **intelligence capabilities** that create clear customer value."
        )


with c4:

    with st.container(
        border=True,
        key="card_navigate"
    ):

        st.caption("04")
        st.subheader("Navigate")

        st.markdown(
            "Turn intelligence into an **MVP, pilot proposition and action plan**."
        )

st.write("")

# =========================================================
# VENTURE PROFILE
# =========================================================

st.markdown(
    '<div class="venture-profile-title">Venture Profile</div>',
    unsafe_allow_html=True
)

st.markdown(
    "**Tell us what you already know.** "
    "Venture Navigator AI will identify assumptions, "
    "gaps and commercial opportunities."
)

st.markdown(
    """
    <div class="vn-trust-panel">
        <div class="vn-trust-title">🔒 Your venture ideas remain yours</div>
        <p class="vn-trust-copy">
            Your venture information is treated as confidential and is processed only to provide
            Venture Navigator analysis. AI Catalyst Studio does not use your venture ideas to develop
            competing products or commercial opportunities.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

with st.form("venture_form"):

    st.markdown("### 1. Venture Basics")
    st.caption("Describe the venture, who it serves and the commercial decision you want to make.")

    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input(
            "Business / Venture Name",
            placeholder="e.g. AI Catalyst Studio"
        )

        website = st.text_input(
            "Website",
            placeholder="https://example.com"
        )

        venture_category = st.selectbox(
            "Venture Category / Industry",
            [
                "AI / Software",
                "Healthcare / HealthTech",
                "Financial Services / FinTech",
                "Education / EdTech",
                "Insurance / InsurTech",
                "Logistics / Transport",
                "Manufacturing / Industrial",
                "Retail / E-commerce",
                "Energy / Utilities",
                "Real Estate / PropTech",
                "Legal / RegTech",
                "Agriculture / AgriTech",
                "Media / Content",
                "Cybersecurity",
                "Professional Services",
                "Other"
            ]
        )

        stage = st.selectbox(
            "Current Stage",
            [
                "Idea",
                "Pre-MVP",
                "MVP",
                "Pilot / Beta",
                "Early Revenue",
                "Growth",
                "Established Business"
            ]
        )

        geography_choice = st.selectbox(
            "Target Geography",
            [
                "South Africa",
                "Southern Africa",
                "Africa",
                "United Kingdom",
                "Europe",
                "North America",
                "Global",
                "Other / Custom"
            ]
        )
        geography_custom = st.text_input(
            "Custom Geography (use when Other / Custom is selected)",
            placeholder="e.g. Gauteng, GCC, Australia",
            help="This field stays editable inside the form. It is used as the target geography only when 'Other / Custom' is selected above."
        )

    with col2:
        customer_type = st.selectbox(
            "Target Customer Type",
            [
                "Consumer",
                "SME / Small Business",
                "Mid-market Business",
                "Enterprise",
                "Government / Public Sector",
                "Healthcare Provider",
                "Educational Institution",
                "Industrial / Manufacturing",
                "Financial Services",
                "Retail / E-commerce",
                "Logistics / Transport",
                "Energy / Utilities",
                "Professional Services",
                "Non-profit / NGO",
                "Other"
            ]
        )

        target_customer = st.text_area(
            "Target Customer",
            placeholder="Who specifically buys or uses the solution?",
            height=105
        )

        revenue_model = st.selectbox(
            "Revenue Model",
            [
                "SaaS subscription",
                "Usage-based pricing",
                "Enterprise contract",
                "One-time software licence",
                "Consulting / services",
                "Transaction fee",
                "Marketplace commission",
                "Advertising / sponsorship",
                "Hardware sale",
                "Hardware + software bundle",
                "Freemium",
                "Not decided yet",
                "Other"
            ]
        )

        primary_goal = st.selectbox(
            "Primary Decision",
            [
                "Strongest market opportunity",
                "Product differentiation",
                "Best target market",
                "MVP definition",
                "Commercial viability",
                "Go-to-market direction",
                "Investor readiness",
                "Indicative venture valuation"
            ]
        )

    offering = st.text_area(
        "Product / Service / Business Offering",
        placeholder=(
            "Describe the offering, the problem being solved "
            "and the capabilities that already exist."
        ),
        height=165
    )

    st.markdown("### 2. Market Context")
    st.caption("Add what you already know. Venture Navigator will identify missing evidence and assumptions.")

    market1, market2, market3 = st.columns(3)

    with market1:
        problem_urgency = st.selectbox(
            "Problem Urgency",
            ["Low", "Moderate", "High", "Mission-critical", "Unknown"]
        )

    with market2:
        delivery_type = st.selectbox(
            "Product Delivery Type",
            [
                "Web application",
                "Mobile application",
                "Desktop application",
                "API / Platform service",
                "Internal business tool",
                "AI assistant / Copilot",
                "Marketplace",
                "Hardware-enabled solution",
                "Hybrid",
                "Not decided yet"
            ]
        )

    with market3:
        data_sensitivity = st.selectbox(
            "Data Sensitivity",
            [
                "Low",
                "Moderate",
                "High",
                "Regulated / Highly sensitive",
                "Unknown / Not applicable"
            ]
        )

    col3, col4 = st.columns(2)

    with col3:
        known_competitors = st.text_area(
            "Known Competitors / Alternatives",
            placeholder=(
                "Competitors, products, websites or what customers "
                "currently use instead."
            ),
            height=110
        )

    with col4:
        constraints = st.text_area(
            "Important Constraints",
            placeholder=(
                "Budget, time, regulation, geography, technology, "
                "resources, integrations..."
            ),
            height=110
        )

    pre_commercial_stages = {"Idea", "Pre-MVP", "MVP"}
    validation_stage = (stage == "Pilot / Beta")
    commercial_stage = stage in {"Early Revenue", "Growth", "Established Business"}

    if stage in pre_commercial_stages:
        st.markdown("### 3. Validation & Readiness Information")
    elif validation_stage:
        st.markdown("### 3. Pilot & Commercial Validation")
    else:
        st.markdown("### 3. Commercial & Traction Information")
    st.caption("Inputs adapt to the venture stage so you are only asked for evidence that should reasonably exist now.")

    fin1, fin2 = st.columns(2)

    with fin1:
        currency = st.selectbox(
            "Reporting Currency",
            ["ZAR", "USD", "GBP", "EUR", "AED", "AUD", "CAD", "Other"]
        )
        team_size = st.number_input(
            "Core Team Size",
            min_value=0,
            step=1,
            value=0
        )

    with fin2:
        months_in_development = st.number_input(
            "Months in Development / Operation",
            min_value=0,
            step=1,
            value=0
        )

    # Commercial metrics are intentionally hidden until they are stage-appropriate.
    paying_customers = None
    monthly_revenue = None
    funding_raised = None

    if pre_commercial_stages:
        if stage in pre_commercial_stages:
            st.info(
                "Revenue, paying-customer and funding metrics are not expected at this stage and are not used as negative evidence. "
                "Venture Navigator will assess validation, team capability, commercial logic and execution readiness instead."
            )

    if validation_stage:
        st.caption("Pilot / Beta stage: commercial metrics are optional. Enter them only if the pilot or beta is already paid or externally funded.")
        v1, v2, v3 = st.columns(3)
        with v1:
            paying_customers = st.number_input(
                "Paying Pilot / Beta Customers (optional)",
                min_value=0, step=1, value=0
            )
        with v2:
            monthly_revenue = st.number_input(
                "Current Monthly Revenue (optional)",
                min_value=0.0, step=1000.0, value=0.0
            )
        with v3:
            funding_raised = st.number_input(
                "Funding Raised to Date (optional)",
                min_value=0.0, step=10000.0, value=0.0
            )

    if commercial_stage:
        c1, c2, c3 = st.columns(3)
        with c1:
            paying_customers = st.number_input(
                "Paying Customers",
                min_value=0, step=1, value=0
            )
        with c2:
            monthly_revenue = st.number_input(
                "Current Monthly Revenue",
                min_value=0.0, step=1000.0, value=0.0
            )
        with c3:
            funding_raised = st.number_input(
                "Funding Raised to Date",
                min_value=0.0, step=10000.0, value=0.0
            )

    traction1, traction2 = st.columns(2)

    stage_traction_options = {
        "Idea": [
            "No validation yet", "Informal feedback", "Customer discovery",
            "Waitlist / expressions of interest", "Letters of intent"
        ],
        "Pre-MVP": [
            "No validation yet", "Customer discovery", "Concept / prototype tested",
            "Waitlist / expressions of interest", "Letters of intent"
        ],
        "MVP": [
            "Prototype tested", "MVP built", "Pilot / design partners",
            "Beta users", "Letters of intent"
        ],
        "Pilot / Beta": [
            "Pilot / design partners", "Beta users", "Paying pilot customers",
            "Signed pilot contracts", "Early repeat usage"
        ],
        "Early Revenue": [
            "Paying customers", "Repeat customers", "Recurring revenue",
            "Signed contracts", "Growing pipeline"
        ],
        "Growth": [
            "Repeat / growing revenue", "Recurring revenue", "Growing customer base",
            "Expansion revenue", "Channel / strategic partnerships"
        ],
        "Established Business": [
            "Established recurring revenue", "Repeat customers", "Multi-year contracts",
            "Expansion revenue", "Strategic partnerships"
        ],
    }

    with traction1:
        traction_stage = st.selectbox(
            "Traction Stage",
            stage_traction_options.get(stage, ["No validation yet"])
        )

    with traction2:
        defensibility_types = st.multiselect(
            "Defensibility Types",
            [
                "Proprietary data",
                "Technical IP / algorithms",
                "Unique workflow integrations",
                "Domain expertise / know-how",
                "Distribution advantage",
                "Regulatory / compliance moat",
                "Strategic partnerships",
                "Brand / community",
                "Network effects",
                "Switching costs",
                "Patents / registered IP",
                "None yet"
            ],
            placeholder="Select all that apply"
        )

    evidence_options_by_stage = {
        "Idea": [
            "No validation yet", "Informal feedback only", "Customer interviews completed",
            "Waitlist / expressions of interest", "Letters of intent", "Other"
        ],
        "Pre-MVP": [
            "No validation yet", "Informal feedback only", "Customer interviews completed",
            "Prototype concept tested", "Waitlist / expressions of interest", "Letters of intent", "Other"
        ],
        "MVP": [
            "Customer interviews completed", "Prototype tested", "MVP usability evidence",
            "Letters of intent", "Pilot users / design partners", "Beta users", "Other"
        ],
        "Pilot / Beta": [
            "Pilot users / design partners", "Beta users", "Paying pilot customers",
            "Signed pilot contracts", "Usage / engagement evidence", "Repeat usage",
            "Strategic partnership", "Other"
        ],
        "Early Revenue": [
            "Paying customers", "Repeat customers", "Signed contracts",
            "Recurring revenue evidence", "Usage / engagement evidence", "Strategic partnership", "Other"
        ],
        "Growth": [
            "Paying customers", "Repeat customers", "Signed contracts", "Recurring revenue evidence",
            "Retention evidence", "Growth evidence", "Strategic partnership", "Other"
        ],
        "Established Business": [
            "Paying customers", "Repeat customers", "Signed contracts", "Recurring revenue evidence",
            "Retention evidence", "Growth evidence", "Multi-year contracts", "Strategic partnership", "Other"
        ],
    }

    traction_evidence_types = st.multiselect(
        "Traction Evidence Types",
        evidence_options_by_stage.get(stage, ["No validation yet", "Other"]),
        placeholder="Select all evidence types that apply"
    )

    traction_notes = st.text_area(
        "Traction / Validation Evidence — Details",
        placeholder=(
            "Add numbers, named pilots, outcomes, usage evidence, commitments, conversion intent "
            "or other proof supporting the selected traction evidence."
        ),
        height=105
    )

    defensibility = st.text_area(
        "Defensibility / Intellectual Property",
        placeholder=(
            "Describe the proprietary technology, data, integrations, know-how, "
            "exclusive relationships or other barriers to replication."
        ),
        height=95
    )

    st.caption(
        "🔒 Financial and venture information is used only to generate your analysis. "
        "AI Catalyst Studio does not use submitted venture ideas for competing commercial opportunities."
    )

    submit = st.form_submit_button(
        "Analyse My Venture",
        use_container_width=True
    )

# Resolve flexible display values after form submission.
geography = geography_custom.strip() if geography_choice == "Other / Custom" and geography_custom.strip() else geography_choice
defensibility_type_text = ", ".join(defensibility_types) if defensibility_types else "None declared"

def stage_metric_text(value, label):
    if value is None:
        return f"Not applicable at {stage} stage"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)

paying_customers_prompt = stage_metric_text(paying_customers, "Paying customers")
monthly_revenue_prompt = stage_metric_text(monthly_revenue, "Current monthly revenue")
funding_raised_prompt = stage_metric_text(funding_raised, "Funding raised to date")

# =========================================================
# INTELLIGENCE PROMPT
# =========================================================

def create_analysis_prompt():

    deterministic_readiness, deterministic_differentiation, deterministic_areas = calculate_deterministic_scores(
        stage=stage,
        problem_urgency=problem_urgency,
        known_competitors=known_competitors,
        offering=offering,
        target_customer=target_customer,
        revenue_model=revenue_model,
        team_size=team_size,
        months_in_development=months_in_development,
        traction_evidence_types=traction_evidence_types,
        traction_notes=traction_notes,
        defensibility_types=defensibility_types,
        defensibility=defensibility,
        paying_customers=paying_customers,
        monthly_revenue=monthly_revenue,
    )

    return f"""
You are the Venture Intelligence Engine inside Venture Navigator AI.

You are not a generic chatbot.

Act as a disciplined market intelligence,
venture discovery and commercial strategy system.

VENTURE INPUT

Business:
{company_name}

Website:
{website}

Stage:
{stage}

Venture category / industry:
{venture_category}

Target geography:
{geography}

Target customer type:
{customer_type}

Target customer:
{target_customer}

Revenue model:
{revenue_model}

Primary decision:
{primary_goal}

Offering:
{offering}

Known competitors:
{known_competitors}

Problem urgency:
{problem_urgency}

Product delivery type:
{delivery_type}

Data sensitivity:
{data_sensitivity}

Constraints:
{constraints}

COMMERCIAL & TRACTION INPUTS

Reporting currency:
{currency}

Core team size:
{team_size}

Paying customers:
{paying_customers_prompt}

Current monthly revenue:
{monthly_revenue_prompt}

Funding raised to date:
{funding_raised_prompt}

Months in development / operation:
{months_in_development}

Traction stage:
{traction_stage}

Traction evidence types:
{", ".join(traction_evidence_types) if traction_evidence_types else "None selected"}

Traction / validation evidence details:
{traction_notes}

Defensibility types selected:
{defensibility_type_text}

Defensibility / intellectual property details:
{defensibility}

Treat zero values as unknown or not yet applicable unless the stage/context clearly indicates otherwise.
Do not infer audited financial performance from user-entered values.

STAGE-ADJUSTED EVIDENCE RULES

Judge the venture against evidence that is appropriate to its CURRENT STAGE.
Do not penalise a venture for evidence that should not reasonably exist yet.

- Idea / Pre-MVP: revenue, paying customers and funding are NOT expected. Financial Evidence means the coherence of the commercial model, pricing hypothesis, expected costs/funding needs and evidence that a customer may eventually pay. Customer Validation should focus on discovery, problem evidence, interviews, expressions of interest and letters of intent.
- MVP: revenue is still NOT required. Focus on functional product evidence, usability, technical feasibility, target-customer validation, pilot readiness and commercial logic.
- Pilot / Beta: prioritise pilot quality, usage, feedback, conversion intent, paid-pilot evidence where applicable, and evidence that the workflow solves the stated problem. Revenue remains optional.
- Early Revenue: paying-customer quality, revenue quality, repeatability, retention, pricing and acquisition evidence become important.
- Growth / Established Business: expect stronger recurring-revenue, growth, retention, margin, customer-concentration and acquisition evidence where relevant.

If a metric is marked 'Not applicable at [stage] stage', explicitly treat it as NOT APPLICABLE rather than missing, zero, or negative evidence.

APPLICATION-CALCULATED SCORES
These scores are calculated deterministically from structured user evidence and MUST be used exactly in both the human-readable report and the machine-readable JSON:
- Investor Readiness: {deterministic_readiness}/100
- Differentiation: {deterministic_differentiation}/100
- Stage-adjusted Investor Readiness area scores (1-5): {deterministic_areas}
Do not replace these with model-generated numeric scores. Your job is to explain the evidence behind them.

1. BUSINESS INTERPRETATION

Explain:

- what the business actually offers
- likely customer
- customer problem
- value proposition
- assumptions or unclear areas


2. MARKET INTELLIGENCE

Analyse the current market.

Identify:

- market demand drivers
- relevant trends
- buying triggers
- barriers to adoption
- commercial opportunities
- structural market changes

Use current public information where useful.

Separate evidence from inference.


3. COMPETITIVE LANDSCAPE

Identify:

- direct competitors
- indirect competitors
- substitute solutions
- current customer status quo

For major competitors explain:

- offering
- positioning
- apparent strengths
- potential gaps

Do not invent pricing, features or capabilities.


4. OPPORTUNITY GAP DISCOVERY

Identify 3 to 5 commercially meaningful opportunities.

Score each from 1 to 5 for:

- Customer Pain
- Market Accessibility
- Differentiation Potential
- MVP Feasibility
- Revenue Potential

Calculate total score out of 25.

Present as a table.

Explain each score.

Scores are prioritisation indicators,
not objective predictions.


5. DIFFERENTIATION INTELLIGENCE

For the strongest opportunities identify:

- Underserved Customer
- Existing Alternative
- Market Gap
- Differentiated Capability
- Commercial Value

Do not describe merely "using AI" as differentiation.

Explain specifically what intelligence the AI performs.


6. MVP NAVIGATOR

Define the smallest credible MVP.

Separate:

MUST HAVE

NICE TO HAVE LATER

DO NOT BUILD YET

Also identify:

- required data
- integrations
- key validation metric
- three highest-risk assumptions


7. GO-TO-MARKET

Recommend:

- initial customer profile
- likely buyer
- outreach angle
- demo storyline
- pilot offering
- evidence needed before scaling


8. RISK ANALYSIS

Assess:

- Market Risk
- Product Risk
- Adoption Risk
- Competitive Risk
- Technical Risk

Explain how each can be tested cheaply.


9. INVESTOR READINESS PRE-ASSESSMENT

Assess readiness across:

- Market Evidence
- Product / MVP Maturity
- Customer Validation
- Commercial Model
- Team / Execution Capacity
- Defensibility
- Financial Evidence

Score each area from 1 to 5 and explain the evidence behind the score, using the stage-adjusted evidence rules above.
Do not reduce a score because revenue, paying customers or funding are absent when those metrics are not appropriate to the current stage.
For Financial Evidence at Idea / Pre-MVP / MVP, score commercial and financial preparedness rather than realised revenue.
After the seven area scores, normalise the overall Investor Readiness result to a 0-100 score and present the /100 score prominently. Do not use the raw /35 total as the headline score.
Do not claim the venture is investment-ready merely because the idea is attractive.
Identify the three most important stage-appropriate gaps that should be closed before approaching investors.

10. INDICATIVE VENTURE VALUATION

Determine whether there is enough evidence for a responsible indicative valuation range.

If evidence is sufficient or partially sufficient, provide a conservative RANGE in the reporting currency, not a single precise value.
Choose methods appropriate to stage, such as:
- pre-revenue scorecard / risk-factor / comparable venture reasoning
- early-revenue revenue-multiple / comparable company reasoning
- mature cash-flow or earnings methods only when the evidence supports them

Never invent comparable transactions, audited revenue, margins or growth rates.
If public comparable data is weak, say so and lower confidence.
If evidence is too weak, do not provide a monetary range.

State:
- valuation status: Available / Insufficient Evidence
- low estimate and high estimate if available
- method(s) used
- confidence: High / Medium / Low
- short rationale
- key value drivers
- key valuation risks
- evidence needed to improve confidence

11. EVIDENCE QUALITY SUMMARY

Briefly distinguish:
- VERIFIED MARKET EVIDENCE: externally sourced facts or current market evidence
- USER-SUPPLIED EVIDENCE: claims, metrics or traction supplied by the user but not independently verified
- ASSUMPTIONS REQUIRING VALIDATION: material points still inferred or unproven

Rate overall evidence quality as High / Medium / Low and explain why in 3-5 sentences.

12. FINAL DECISION BRIEF

End with:

EXECUTIVE SUMMARY

RECOMMENDED MARKET FOCUS

WHY THIS FOCUS

DIFFERENTIATION STRATEGY

BETA / MVP DEFINITION

IMMEDIATE NEXT 5 ACTIONS

WHAT TO DEFER

KEY UNKNOWN QUESTIONS

CONFIDENCE:
High / Medium / Low

Explain why.

Produce a polished executive business intelligence report.

Avoid generic startup advice.

Recommendations must relate specifically to this venture.

13. MACHINE-READABLE EXECUTIVE BLOCK

At the very end, after the human-readable report, output exactly one JSON object between these tags:
<VN_EXECUTIVE_JSON>
{{
  "opportunity_score": 0,
  "market_attractiveness": "Low|Medium|High",
  "differentiation_score": 0,
  "investor_readiness_score": 0,
  "recommended_next_action": "",
  "evidence_quality": {{
    "overall": "Low|Medium|High",
    "verified_market_evidence": "Low|Medium|High",
    "user_supplied_evidence": "Limited|Moderate|Strong",
    "assumption_load": "Low|Medium|High",
    "summary": ""
  }},
  "valuation": {{
    "status": "Available|Insufficient Evidence",
    "low": null,
    "high": null,
    "method": "",
    "confidence": "Low|Medium|High",
    "rationale": ""
  }},
  "investor_readiness": {{
    "market_evidence": {{"score": 0, "reason": ""}},
    "product_maturity": {{"score": 0, "reason": ""}},
    "customer_validation": {{"score": 0, "reason": ""}},
    "commercial_model": {{"score": 0, "reason": ""}},
    "team_execution": {{"score": 0, "reason": ""}},
    "defensibility": {{"score": 0, "reason": ""}},
    "financial_evidence": {{"score": 0, "reason": ""}}
  }},
  "what_not_to_build": [
    {{"item": "", "reason": ""}}
  ],
  "challenge": {{
    "why_it_may_fail": "",
    "key_assumption": "",
    "what_would_change_the_conclusion": ""
  }},
  "action_plan_90_day": {{
    "days_0_30": [],
    "days_31_60": [],
    "days_61_90": []
  }}
}}
</VN_EXECUTIVE_JSON>

All scores in this JSON block must be integers from 0 to 100.
The application may override Differentiation and Investor Readiness scores with deterministic structured-evidence scoring. Therefore explain the evidence clearly and do not imply that a model-generated score is authoritative.
For valuation.low and valuation.high return numbers only, with no currency symbols or commas.
If valuation status is Insufficient Evidence, low and high must be null in JSON only.
In the HUMAN-READABLE report, never print the literal word "null" for a missing value. Use "Not available" or "Insufficient evidence" instead.
Keep the report concise and avoid repeating the same recommendation in multiple sections unless needed for the final decision brief.
Do not place markdown fences around the JSON.
"""


# =========================================================
# STRUCTURED EXECUTIVE OUTPUT
# =========================================================

def extract_executive_json(report_text):
    """Extract the machine-readable Venture Navigator executive block."""
    match = re.search(
        r"<VN_EXECUTIVE_JSON>\s*(\{.*?\})\s*</VN_EXECUTIVE_JSON>",
        report_text,
        flags=re.DOTALL,
    )
    if not match:
        return None, report_text

    try:
        data = json.loads(match.group(1))
    except Exception:
        return None, report_text

    clean_report = re.sub(
        r"\s*<VN_EXECUTIVE_JSON>.*?</VN_EXECUTIVE_JSON>\s*",
        "\n",
        report_text,
        flags=re.DOTALL,
    ).strip()
    return data, clean_report


def polish_human_report(report_text):
    """Remove technical placeholder leakage from the user-facing report."""
    text = report_text or ""
    text = re.sub(r"(?i)(Low estimate\s*[:\-]\s*)null", r"\1Not available", text)
    text = re.sub(r"(?i)(High estimate\s*[:\-]\s*)null", r"\1Not available", text)
    text = re.sub(r"(?i)(Valuation range\s*[:\-]\s*)null", r"\1Insufficient evidence", text)

    def normalise_readiness(match):
        try:
            raw = float(match.group(2))
            normalised = max(0, min(100, round(raw / 35 * 100)))
            return f"{match.group(1)}{normalised}/100"
        except Exception:
            return match.group(0)

    text = re.sub(
        r"(?i)(Overall investor readiness\s*[:\-]\s*)(\d+(?:\.\d+)?)\s*/\s*35",
        normalise_readiness,
        text,
    )
    return text


def clamp_score(value, low=0, high=100):
    try:
        return max(low, min(high, int(round(float(value)))))
    except Exception:
        return 0




def calculate_deterministic_scores(
    stage, problem_urgency, known_competitors, offering, target_customer, revenue_model,
    team_size, months_in_development, traction_evidence_types, traction_notes,
    defensibility_types, defensibility, paying_customers, monthly_revenue
):
    """Calculate stable, stage-aware dashboard scores from structured venture evidence.

    These scores deliberately do not depend on the language model's numeric judgement.
    The model may explain them, but the application owns the score.
    """
    traction_set = set(traction_evidence_types or [])
    defense_set = set(defensibility_types or [])
    notes_present = bool((traction_notes or '').strip())
    defense_notes_present = bool((defensibility or '').strip())

    # Market evidence (1-5): structured problem/customer definition + evidence signals.
    market = 1
    if problem_urgency in {"Moderate", "High", "Mission-critical"}: market += 1
    if (target_customer or '').strip(): market += 1
    if (known_competitors or '').strip(): market += 1
    if traction_set.intersection({
        "Customer interviews completed", "Waitlist / expressions of interest",
        "Letters of intent", "Pilot users / design partners", "Beta users",
        "Paying pilot customers", "Paying customers", "Signed contracts",
        "Recurring revenue evidence", "Usage / engagement evidence", "Repeat usage",
        "Repeat customers", "Growth evidence", "Retention evidence"
    }): market += 1
    market = min(5, market)
    # At Idea/Pre-MVP stage, market evidence cannot be "very strong" without
    # venture-specific validation. External market attractiveness alone is not enough.
    if stage in {"Idea", "Pre-MVP"}:
        market = min(4, market)

    stage_product_base = {
        "Idea": 1, "Pre-MVP": 2, "MVP": 3, "Pilot / Beta": 3,
        "Early Revenue": 4, "Growth": 4, "Established Business": 5
    }.get(stage, 1)
    product = stage_product_base
    if months_in_development and months_in_development >= 3: product += 1
    product = min(5, product)

    # Customer validation is evidence-driven, not stage-label driven.
    validation_weights = {
        "No validation yet": 0, "Informal feedback only": 1, "Customer interviews completed": 2,
        "Prototype concept tested": 2, "Prototype tested": 2, "MVP usability evidence": 2,
        "Waitlist / expressions of interest": 2, "Letters of intent": 3,
        "Pilot users / design partners": 3, "Beta users": 3,
        "Paying pilot customers": 4, "Signed pilot contracts": 4,
        "Usage / engagement evidence": 3, "Repeat usage": 4,
        "Paying customers": 4, "Repeat customers": 5, "Signed contracts": 5,
        "Recurring revenue evidence": 5, "Retention evidence": 5,
        "Growth evidence": 5, "Multi-year contracts": 5, "Strategic partnership": 3,
        "Other": 1
    }
    customer_validation = max([validation_weights.get(x, 0) for x in traction_set] + [0])
    if notes_present and customer_validation < 5: customer_validation += 1
    customer_validation = max(1, min(5, customer_validation))

    # Commercial readiness measures evidence of a workable commercial model, not merely
    # the fact that the founder selected a revenue-model label. Early-stage ventures are
    # kept neutral rather than rewarded for untested assumptions.
    commercial = 1
    if revenue_model and revenue_model not in {"Not decided yet", "Other"}: commercial += 1
    if (offering or '').strip() and (target_customer or '').strip(): commercial += 1
    if traction_set.intersection({
        "Letters of intent", "Paying pilot customers", "Signed pilot contracts",
        "Paying customers", "Signed contracts", "Recurring revenue evidence",
        "Repeat customers", "Multi-year contracts"
    }): commercial += 1
    if stage in {"Idea", "Pre-MVP"}:
        commercial = min(3, commercial)
    elif stage == "MVP":
        commercial = min(4, commercial)
    else:
        commercial = min(5, commercial)

    team = 1
    if team_size and team_size >= 1: team += 1
    if team_size and team_size >= 2: team += 1
    if team_size and team_size >= 4: team += 1
    if months_in_development and months_in_development >= 6: team += 1
    team = min(5, team)

    meaningful_defenses = defense_set - {"None yet"}
    defense_detail = (defensibility or '').strip()
    defense_detail_len = len(defense_detail)

    # Selected moat types are founder claims, not proof. They create only a modest base
    # score until the user supplies substantive evidence of ownership, exclusivity,
    # measured switching costs, protected IP, unique data rights or hard-to-copy integrations.
    defensibility_score_5 = 1
    if meaningful_defenses:
        defensibility_score_5 += 1
    if defense_detail_len >= 120:
        defensibility_score_5 += 1
    if defense_detail_len >= 240 and any(x in meaningful_defenses for x in {
        "Proprietary data", "Patents / registered IP", "Unique workflow integrations",
        "Regulatory / compliance moat", "Switching costs", "Network effects"
    }):
        defensibility_score_5 += 1
    if traction_set.intersection({"Strategic partnership", "Signed contracts", "Multi-year contracts"}):
        defensibility_score_5 += 1
    if stage in {"Idea", "Pre-MVP"}:
        defensibility_score_5 = min(3, defensibility_score_5)
    defensibility_score_5 = min(5, defensibility_score_5)

    # Financial preparedness is stage-adjusted. "Not applicable" remains neutral: it
    # avoids a penalty, but it does not earn positive readiness points. Early-stage
    # ventures score on commercial preparedness signals rather than realised revenue.
    if stage in {"Idea", "Pre-MVP"}:
        financial = 1
        if revenue_model and revenue_model not in {"Not decided yet", "Other"}: financial += 1
        if traction_set.intersection({"Paying pilot customers", "Signed pilot contracts"}):
            financial += 1
        financial = min(3, financial)
    elif stage == "MVP":
        financial = 1
        if revenue_model and revenue_model not in {"Not decided yet", "Other"}: financial += 1
        if traction_set.intersection({"Letters of intent", "Paying pilot customers", "Signed pilot contracts"}):
            financial += 1
        if notes_present: financial += 1
        financial = min(4, financial)
    elif stage == "Pilot / Beta":
        financial = 1
        if revenue_model and revenue_model not in {"Not decided yet", "Other"}: financial += 1
        if (paying_customers or 0) > 0 or (monthly_revenue or 0) > 0: financial += 1
        if traction_set.intersection({"Signed pilot contracts", "Paying pilot customers", "Signed contracts"}):
            financial += 1
        financial = min(4, financial)
    else:
        financial = 1
        if (paying_customers or 0) > 0: financial += 1
        if (monthly_revenue or 0) > 0: financial += 1
        if revenue_model and revenue_model not in {"Not decided yet", "Other"}: financial += 1
        if traction_set.intersection({"Recurring revenue evidence", "Retention evidence", "Growth evidence", "Multi-year contracts"}):
            financial += 1
        financial = min(5, financial)

    area_scores = {
        "market_evidence": market,
        "product_maturity": product,
        "customer_validation": customer_validation,
        "commercial_model": commercial,
        "team_execution": team,
        "defensibility": defensibility_score_5,
        "financial_evidence": financial,
    }
    investor_readiness = round(sum(area_scores.values()) / 35 * 100)

    # Differentiation is independent of stage and evidence-weighted. Selecting a moat
    # type is treated as a claim; stronger scores require a defined wedge, competitor
    # awareness and substantive supporting detail.
    differentiation = 15
    if (target_customer or '').strip(): differentiation += 10
    if (offering or '').strip(): differentiation += 10
    if (known_competitors or '').strip(): differentiation += 10
    differentiation += min(15, len(meaningful_defenses) * 3)
    if defense_detail_len >= 120: differentiation += 8
    if defense_detail_len >= 240 and any(x in meaningful_defenses for x in {
        "Proprietary data", "Patents / registered IP", "Unique workflow integrations",
        "Regulatory / compliance moat", "Switching costs", "Network effects"
    }): differentiation += 7
    if traction_set.intersection({"Pilot users / design partners", "Paying pilot customers", "Signed pilot contracts",
                                  "Paying customers", "Signed contracts", "Repeat customers", "Strategic partnership"}):
        differentiation += 5
    differentiation = max(0, min(100, differentiation))

    return investor_readiness, differentiation, area_scores


def apply_deterministic_scores(executive_data, **kwargs):
    if not executive_data:
        return executive_data
    readiness, differentiation, area_scores = calculate_deterministic_scores(**kwargs)
    executive_data["investor_readiness_score"] = readiness
    executive_data["differentiation_score"] = differentiation

    breakdown = executive_data.setdefault("investor_readiness", {})
    for key, score5 in area_scores.items():
        entry = breakdown.setdefault(key, {})
        entry["score"] = round(score5 / 5 * 100)
        entry["stage_adjusted_score_5"] = score5
    return executive_data


def render_executive_dashboard(data, currency_code="ZAR"):
    if not data:
        return

    st.markdown("## Executive Intelligence Dashboard")
    st.caption(
        "Decision-support indicators derived from the venture evidence supplied and current market analysis. "
        "Scores are directional, not guarantees."
    )

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Opportunity Score", f"{clamp_score(data.get('opportunity_score'))}/100")
    d2.metric("Market Attractiveness", str(data.get('market_attractiveness', 'Not assessed')))
    d3.metric("Differentiation", f"{clamp_score(data.get('differentiation_score'))}/100")
    d4.metric("Investor Readiness", f"{clamp_score(data.get('investor_readiness_score'))}/100")
    st.caption("Opportunity Score combines customer pain, market accessibility, differentiation potential, MVP feasibility and revenue potential.")

    evidence = data.get("evidence_quality") or {}
    if isinstance(evidence, dict) and evidence:
        with st.container(border=True):
            st.markdown("### Evidence Quality")
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Overall", str(evidence.get("overall", "Not assessed")))
            e2.metric("Verified Market Evidence", str(evidence.get("verified_market_evidence", "Not assessed")))
            e3.metric("User-Supplied Evidence", str(evidence.get("user_supplied_evidence", "Not assessed")))
            e4.metric("Assumption Load", str(evidence.get("assumption_load", "Not assessed")))
            if evidence.get("summary"):
                st.caption(str(evidence.get("summary")))

    val = data.get("valuation") or {}
    valuation_status = str(val.get("status", "Not assessed"))
    valuation_low = val.get("low")
    valuation_high = val.get("high")
    confidence = str(val.get("confidence", "Low"))
    method = str(val.get("method", "Insufficient evidence"))

    with st.container(border=True):
        st.markdown("### Indicative Venture Valuation")
        if valuation_status.lower() == "available" and valuation_low is not None and valuation_high is not None:
            try:
                low = float(valuation_low)
                high = float(valuation_high)
                st.markdown(f"# {currency_code} {low:,.0f} – {currency_code} {high:,.0f}")
            except Exception:
                st.markdown("**Valuation range unavailable**")
        else:
            st.markdown("**Insufficient evidence for a responsible monetary range**")
        st.caption(f"Method: {method} • Confidence: {confidence}")
        st.caption("Indicative decision-support estimate only — not a formal business valuation, investment opinion or fairness opinion.")
        rationale = val.get("rationale")
        if rationale:
            st.write(rationale)

    next_action = data.get("recommended_next_action")
    if next_action:
        st.success(f"**Recommended next action:** {next_action}")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("### What Not to Build Yet")
            items = data.get("what_not_to_build") or []
            if items:
                for item in items[:3]:
                    if isinstance(item, dict):
                        st.markdown(f"**{item.get('item','Option')}** — {item.get('reason','')}")
                    else:
                        st.markdown(f"- {item}")
            else:
                st.write("No specific defer recommendation returned.")

    with right:
        with st.container(border=True):
            st.markdown("### Challenge This Recommendation")
            challenge = data.get("challenge") or {}
            if isinstance(challenge, dict):
                if challenge.get("why_it_may_fail"):
                    st.markdown(f"**Why it may fail:** {challenge['why_it_may_fail']}")
                if challenge.get("key_assumption"):
                    st.markdown(f"**Key assumption:** {challenge['key_assumption']}")
                if challenge.get("what_would_change_the_conclusion"):
                    st.markdown(
                        f"**What would change the conclusion:** {challenge['what_would_change_the_conclusion']}"
                    )

    readiness = data.get("investor_readiness") or {}
    if isinstance(readiness, dict) and readiness:
        st.markdown("### Investor Readiness Breakdown")
        rows = []
        for label, value in readiness.items():
            if isinstance(value, dict):
                rows.append({
                    "Area": label.replace("_", " ").title(),
                    "Score": clamp_score(value.get("score")),
                    "Evidence / Gap": value.get("reason", ""),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    plan = data.get("action_plan_90_day") or {}
    if isinstance(plan, dict) and plan:
        st.markdown("### 90-Day Action Plan")
        p1, p2, p3 = st.columns(3)
        for col, key, title in [(p1,"days_0_30","0–30 Days"),(p2,"days_31_60","31–60 Days"),(p3,"days_61_90","61–90 Days")]:
            with col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    values = plan.get(key) or []
                    for item in values[:5]:
                        st.markdown(f"- {item}")

# =========================================================
# RUN ENGINE
# =========================================================

if submit:

    stage_validation_error = None
    if stage == "Early Revenue" and (paying_customers or 0) <= 0 and (monthly_revenue or 0) <= 0:
        stage_validation_error = (
            "Early Revenue requires evidence of commercial activity. Enter at least one paying customer "
            "or non-zero monthly revenue, or select an earlier venture stage."
        )
    elif stage in {"Growth", "Established Business"} and ((paying_customers or 0) <= 0 or (monthly_revenue or 0) <= 0):
        stage_validation_error = (
            f"{stage} requires both paying-customer and revenue evidence. Enter the commercial metrics, "
            "or select an earlier venture stage."
        )

    if not OPENAI_API_KEY:

        st.error(
            "OPENAI_API_KEY was not found in the project .env file."
        )

    elif stage_validation_error:

        st.error(stage_validation_error)

    elif not offering.strip():

        st.warning(
            "Please describe the business offering before generating the report."
        )

    else:

        st.divider()

        with st.container(border=True):

            st.caption(
                "VENTURE NAVIGATOR AI"
            )

            st.header(
                "Venture Intelligence Report"
            )

            st.write(
                "Market • Competition • Opportunity • Differentiation • MVP"
            )

        with st.status(
            "Running Venture Intelligence Engine...",
            expanded=True
        ) as status:

            st.write(
                "Understanding the venture proposition..."
            )

            st.write(
                "Researching current market conditions..."
            )

            st.write(
                "Mapping competitors and alternatives..."
            )

            st.write(
                "Discovering market opportunity gaps..."
            )

            st.write(
                "Evaluating differentiation potential..."
            )

            st.write(
                "Defining the MVP and commercial direction..."
            )

            try:

                response = client.responses.create(
                    model=OPENAI_MODEL,
                    tools=[
                        {
                            "type": "web_search"
                        }
                    ],
                    input=create_analysis_prompt()
                )

                raw_report = response.output_text
                executive_data, report = extract_executive_json(raw_report)
                executive_data = apply_deterministic_scores(
                    executive_data,
                    stage=stage,
                    problem_urgency=problem_urgency,
                    known_competitors=known_competitors,
                    offering=offering,
                    target_customer=target_customer,
                    revenue_model=revenue_model,
                    team_size=team_size,
                    months_in_development=months_in_development,
                    traction_evidence_types=traction_evidence_types,
                    traction_notes=traction_notes,
                    defensibility_types=defensibility_types,
                    defensibility=defensibility,
                    paying_customers=paying_customers,
                    monthly_revenue=monthly_revenue,
                )
                report = polish_human_report(report)

                track_usage_event(
                    "report_generated",
                    user=beta_access["user"],
                    venture_name=company_name.strip() if company_name else None,
                    venture_stage=stage,
                    primary_goal=primary_goal,
                    metadata={
                        "geography": geography.strip() if geography else None,
                        "revenue_model": revenue_model.strip() if revenue_model else None,
                        "website_provided": bool(website.strip()) if website else False,
                        "currency": currency.strip() if currency else None,
                        "paying_customers": int(paying_customers) if paying_customers is not None else None,
                        "monthly_revenue": float(monthly_revenue) if monthly_revenue is not None else None,
                        "funding_raised": float(funding_raised) if funding_raised is not None else None,
                    }
                )


                status.update(
                    label="Venture Intelligence analysis complete",
                    state="complete"
                )

                render_executive_dashboard(
                    executive_data,
                    currency_code=(currency.strip().upper() if currency else "ZAR")
                )

                st.divider()
                st.markdown("## Full Venture Intelligence Report")
                st.markdown(report)

                share_summary = (
                    f"Venture Navigator AI generated a Venture Intelligence Report"
                    f"{' for ' + company_name.strip() if company_name and company_name.strip() else ''}.\n\n"
                    f"Primary decision: {primary_goal}\n"
                    f"Stage: {stage}\n"
                    f"Geography: {geography.strip() if geography else 'Not specified'}\n\n"
                    "The report covers market opportunity, competitors, "
                    "differentiation, MVP direction and practical next actions.\n\n"
                    "Generated with Venture Navigator AI:\n"
                    "https://venture.aicatalyststudio.co.za"
                )

                download_col, copy_col, whatsapp_col = st.columns(3)

                with download_col:
                    pdf_report = build_branded_pdf(
                        report,
                        company_name=company_name.strip() if company_name else None,
                        executive_data=executive_data,
                        currency_code=(currency.strip().upper() if currency else "ZAR"),
                        venture_stage=stage,
                        geography=(geography.strip() if geography else None),
                    )

                    st.download_button(
                        "⬇️ Download Branded PDF",
                        data=pdf_report,
                        file_name="venture_navigator_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                with copy_col:
                    import streamlit.components.v1 as components
                    import json

                    copy_payload = json.dumps(report)

                    components.html(
                        f"""
                        <button
                            onclick='navigator.clipboard.writeText({copy_payload}).then(() => {{
                                this.innerText = "✅ Copied";
                                setTimeout(() => this.innerText = "📋 Copy Report", 1500);
                            }})'
                            style="
                                width:100%;
                                height:48px;
                                padding:0;
                                border-radius:8px;
                                border:1px solid #178fc4;
                                background:linear-gradient(90deg,#08678d,#159fd2);
                                color:#ffffff;
                                font-weight:700;
                                font-size:0.95rem;
                                cursor:pointer;
                            "
                        >
                            📋 Copy Report
                        </button>
                        """,
                        height=52
                    )

                with whatsapp_col:
                    import urllib.parse

                    whatsapp_url = (
                        "https://wa.me/?text="
                        + urllib.parse.quote(share_summary)
                    )

                    st.link_button(
                        "📱 Share on WhatsApp",
                        whatsapp_url,
                        use_container_width=True
                    )

                st.caption(
                    "Tip: share the summary on WhatsApp, or download the branded "
                    "PDF and attach it to WhatsApp or email."
                )

            except Exception as error:

                status.update(
                    label="Venture Intelligence analysis failed",
                    state="error"
                )

                st.error(
                    str(error)
                )


# =========================================================
# REPORT ACTION BUTTON STYLING
# =========================================================
st.markdown("""
<style>

/* Report sharing/action buttons */
div[data-testid="stDownloadButton"] > button,
div[data-testid="stLinkButton"] > a {
    width: 100% !important;
    height: 48px !important;
    min-height: 48px !important;
    border-radius: 8px !important;
    border: 1px solid #178fc4 !important;
    background: linear-gradient(90deg, #08678d, #159fd2) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-decoration: none !important;
}

div[data-testid="stDownloadButton"] > button:hover,
div[data-testid="stLinkButton"] > a:hover {
    background: linear-gradient(90deg, #075a7c, #1188b5) !important;
    color: #ffffff !important;
    border-color: #0e789f !important;
}

</style>
""", unsafe_allow_html=True)



# =========================================================
# REPORT / RESULTS CONTRAST FIX
# =========================================================

st.markdown("""
<style>

/* Generated report body text on the light silver results surface */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #27495b;
}

[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    color: #123e58;
}

/* Markdown report tables */
[data-testid="stMarkdownContainer"] table {
    width: 100%;
    border-collapse: collapse;
    color: #213f51 !important;
    background: rgba(238, 242, 245, 0.96) !important;
}

[data-testid="stMarkdownContainer"] table thead tr,
[data-testid="stMarkdownContainer"] table th {
    background: #c8d1d7 !important;
    color: #123e58 !important;
    -webkit-text-fill-color: #123e58 !important;
    font-weight: 800 !important;
}

[data-testid="stMarkdownContainer"] table tbody tr,
[data-testid="stMarkdownContainer"] table td {
    background: #e7ecef !important;
    color: #27495b !important;
    -webkit-text-fill-color: #27495b !important;
    font-weight: 560 !important;
}

[data-testid="stMarkdownContainer"] table th,
[data-testid="stMarkdownContainer"] table td {
    border: 1px solid #b8c3ca !important;
    padding: 0.72rem 0.75rem !important;
    vertical-align: top !important;
}

[data-testid="stMarkdownContainer"] table a {
    color: #087fac !important;
    -webkit-text-fill-color: #087fac !important;
    text-decoration: underline !important;
    font-weight: 700 !important;
}

/* Preserve readable emphasis inside report tables */
[data-testid="stMarkdownContainer"] table strong,
[data-testid="stMarkdownContainer"] table b {
    color: #173f55 !important;
    -webkit-text-fill-color: #173f55 !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Venture Navigator AI • Powered by AI Catalyst Studio • Beta  |  Your venture. Your data. Your intellectual property."
)


# =========================================================
# FINAL VENTURE PROFILE FORM CONTRAST FIX
# =========================================================

st.markdown("""
<style>

/* ======================================================
   VENTURE PROFILE LABELS
====================================================== */

[data-testid="stForm"] [data-testid="stWidgetLabel"] p,
[data-testid="stForm"] label {
    color: #284a5d !important;
    -webkit-text-fill-color: #284a5d !important;
    font-weight: 760 !important;
}


/* ======================================================
   FORM SECTION HEADINGS + HELPER TEXT
====================================================== */

[data-testid="stForm"] h1,
[data-testid="stForm"] h2,
[data-testid="stForm"] h3 {
    color: #143b54 !important;
    -webkit-text-fill-color: #143b54 !important;
}

[data-testid="stForm"] [data-testid="stCaptionContainer"] p {
    color: #5d7888 !important;
    -webkit-text-fill-color: #5d7888 !important;
    font-weight: 680 !important;
}

/* ======================================================
   TEXT / TEXTAREA / SELECT FIELD CONTAINERS
====================================================== */

[data-testid="stForm"] div[data-baseweb="input"] > div,
[data-testid="stForm"] div[data-baseweb="textarea"] > div,
[data-testid="stForm"] div[data-baseweb="select"] > div {

    background: #f1f6fa !important;
    background-color: #f1f6fa !important;

    border: 1px solid #8edbe8 !important;
    border-radius: 11px !important;

    box-shadow:
        inset 0 1px 2px rgba(35,65,85,0.04) !important;
}


/* ======================================================
   ACTUAL INPUT TEXT
====================================================== */

[data-testid="stForm"] input,
[data-testid="stForm"] textarea {

    background: #f1f6fa !important;
    background-color: #f1f6fa !important;

    color: #173b50 !important;
    -webkit-text-fill-color: #173b50 !important;

    caret-color: #173b50 !important;

    font-weight: 600 !important;
}


/* ======================================================
   PLACEHOLDER TEXT
====================================================== */

[data-testid="stForm"] input::placeholder,
[data-testid="stForm"] textarea::placeholder {

    color: #66879b !important;
    -webkit-text-fill-color: #66879b !important;

    opacity: 1 !important;
}


/* ======================================================
   SELECT BOX TEXT
====================================================== */

[data-testid="stForm"] div[data-baseweb="select"] span,
[data-testid="stForm"] div[data-baseweb="select"] div {

    color: #173b50 !important;
    -webkit-text-fill-color: #173b50 !important;
}


/* Dropdown arrow */
[data-testid="stForm"] div[data-baseweb="select"] svg {

    color: #173b50 !important;
    fill: #173b50 !important;
}


/* ======================================================
   SAFARI / CHROME AUTOFILL
====================================================== */

[data-testid="stForm"] input:-webkit-autofill,
[data-testid="stForm"] input:-webkit-autofill:hover,
[data-testid="stForm"] input:-webkit-autofill:focus {

    -webkit-text-fill-color: #173b50 !important;

    -webkit-box-shadow:
        0 0 0 1000px #f1f6fa inset !important;

    box-shadow:
        0 0 0 1000px #f1f6fa inset !important;
}


/* ======================================================
   FOCUS STATE
====================================================== */

[data-testid="stForm"] div[data-baseweb="input"] > div:focus-within,
[data-testid="stForm"] div[data-baseweb="textarea"] > div:focus-within,
[data-testid="stForm"] div[data-baseweb="select"] > div:focus-within {

    border: 1px solid #26c7df !important;

    box-shadow:
        0 0 0 3px rgba(38,199,223,0.13) !important;
}

</style>
""", unsafe_allow_html=True)

