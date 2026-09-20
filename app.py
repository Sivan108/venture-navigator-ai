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
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)



# =========================================================
# BRANDED PDF REPORT
# =========================================================
def build_branded_pdf(report_text, company_name=None):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Venture Navigator AI - Venture Intelligence Report",
        author="AI Catalyst Studio",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "VNTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#123d59"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "VNSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#168fbe"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "VNH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#123d59"),
        spaceBefore=12,
        spaceAfter=7,
    )

    h2_style = ParagraphStyle(
        "VNH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#176c91"),
        spaceBefore=10,
        spaceAfter=5,
    )

    body_style = ParagraphStyle(
        "VNBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#233642"),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "VNBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-7,
        spaceAfter=4,
    )

    story = []

    logo_path = Path("logo_report.jpeg")
    if logo_path.exists():
        img = RLImage(str(logo_path))
        max_width = 165 * mm
        scale = min(max_width / img.imageWidth, 1)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        story.append(img)
        story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "Venture Navigator AI",
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI-Driven Venture and Market Intelligence",
            subtitle_style
        )
    )

    if company_name:
        story.append(
            Paragraph(
                html.escape(company_name),
                ParagraphStyle(
                    "VNCompany",
                    parent=styles["Heading2"],
                    alignment=TA_CENTER,
                    fontSize=12,
                    textColor=colors.HexColor("#344f60"),
                    spaceAfter=6,
                )
            )
        )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#1da7d6"),
            spaceBefore=3,
            spaceAfter=10,
        )
    )

    def fmt_inline(value):
        safe = html.escape(value)
        safe = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            safe
        )
        safe = re.sub(
            r"\*(.+?)\*",
            r"<i>\1</i>",
            safe
        )
        return safe

    for raw_line in report_text.splitlines():
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 2.5 * mm))
            continue

        if line.startswith("### "):
            story.append(
                Paragraph(
                    fmt_inline(line[4:]),
                    h2_style
                )
            )
            continue

        if line.startswith("## "):
            story.append(
                Paragraph(
                    fmt_inline(line[3:]),
                    h1_style
                )
            )
            continue

        if line.startswith("# "):
            story.append(
                Paragraph(
                    fmt_inline(line[2:]),
                    h1_style
                )
            )
            continue

        if line.startswith(("- ", "* ")):
            story.append(
                Paragraph(
                    "• " + fmt_inline(line[2:]),
                    bullet_style
                )
            )
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)", line)
        if numbered:
            story.append(
                Paragraph(
                    f"{numbered.group(1)}. "
                    + fmt_inline(numbered.group(2)),
                    bullet_style
                )
            )
            continue

        story.append(
            Paragraph(
                fmt_inline(line),
                body_style
            )
        )

    story.append(Spacer(1, 8 * mm))

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.7,
            color=colors.HexColor("#9bb7c7"),
            spaceBefore=4,
            spaceAfter=6,
        )
    )

    story.append(
        Paragraph(
            "Generated by Venture Navigator AI - AI Catalyst Studio<br/>"
            "https://venture.aicatalyststudio.co.za",
            ParagraphStyle(
                "VNFooter",
                parent=styles["Normal"],
                fontSize=8,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#607986"),
            )
        )
    )

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
   FOUR NAVY CARDS
------------------------------------------------------- */

.st-key-card_understand,
.st-key-card_discover,
.st-key-card_differentiate,
.st-key-card_navigate {

    background:
        linear-gradient(
            145deg,
            #0c3047 0%,
            #124560 100%
        ) !important;

    border:
        1px solid rgba(27, 195, 221, 0.28) !important;

    border-radius:
        14px !important;

    box-shadow:
        0 12px 26px rgba(31, 58, 76, 0.19) !important;
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
        #ffffff !important;
}

.st-key-card_understand [data-testid="stCaptionContainer"] p,
.st-key-card_discover [data-testid="stCaptionContainer"] p,
.st-key-card_differentiate [data-testid="stCaptionContainer"] p,
.st-key-card_navigate [data-testid="stCaptionContainer"] p {

    color:
        #c5a842 !important;

    font-weight:
        850 !important;
}


/* -------------------------------------------------------
   CAPTIONS
------------------------------------------------------- */

div[data-testid="stCaptionContainer"] p {
    color: #7894a5 !important;
    font-weight: 750 !important;
}


/* -------------------------------------------------------
   VENTURE PROFILE TITLE
------------------------------------------------------- */

.venture-profile-title {
    color: #35d8ef !important;
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
        radial-gradient(
            circle at 90% 8%,
            rgba(35, 226, 243, 0.15),
            transparent 28%
        ),
        linear-gradient(
            110deg,
            #082b3d 0%,
            #0a4259 38%,
            #0b617c 68%,
            #247cc1 100%
        ) !important;

    border:
        1px solid rgba(23, 216, 237, 0.46) !important;

    border-radius:
        22px !important;

    padding:
        1.65rem !important;

    box-shadow:
        0 18px 42px rgba(28, 67, 91, 0.24);
}


/* -------------------------------------------------------
   FORM LABELS
------------------------------------------------------- */

label,
div[data-testid="stWidgetLabel"] p {
    color: #ffffff !important;
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
# REGISTRATION + 7-DAY BETA ACCESS
# =========================================================

beta_access = require_beta_access()


# =========================================================
# AI CATALYST STUDIO WEBSITE HEADER
# =========================================================
if os.path.exists("logo_dark.jpeg"):
    top_logo_left, top_logo_mid, top_logo_right = st.columns(
        [1.2, 5.6, 1.2]
    )

    with top_logo_mid:
        st.image(
            "logo_dark.jpeg",
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
                "Active Trials",
                active_trials
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
            # USER / TRIAL STATUS
            # -------------------------------------------------
            st.markdown("#### Beta Users")

            user_rows = []

            for user in users:
                registered = user.get("registered_at")
                last_login = user.get("last_login_at")

                trial_status = "Unknown"
                days_remaining = None

                if registered:
                    try:
                        created = datetime.fromisoformat(
                            registered.replace("Z", "+00:00")
                        )

                        end = created + timedelta(days=7)
                        remaining = end - now

                        if remaining.total_seconds() > 0:
                            trial_status = "Active"
                            days_remaining = max(
                                1,
                                remaining.days + (
                                    1 if remaining.seconds else 0
                                )
                            )
                        else:
                            trial_status = "Expired"
                            days_remaining = 0

                    except Exception:
                        pass

                user_report_count = sum(
                    1
                    for event in report_events
                    if event.get("user_id") == user.get("user_id")
                )

                user_rows.append(
                    {
                        "Email": user.get("email"),
                        "Registered": registered,
                        "Last Login": last_login,
                        "Trial": trial_status,
                        "Days Left": days_remaining,
                        "Reports": user_report_count,
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
                f"Expired trials: {expired_trials} • "
                f"Login events recorded: {len(login_events)}"
            )

        except Exception as stats_error:
            st.warning(
                f"Stats board could not be loaded: {stats_error}"
            )



# =========================================================
# HERO
# =========================================================

logo_path = "logo_2.jpeg"

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
            "Find specific **intelligence capabilities** that could create customer value."
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

with st.form("venture_form"):

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

        stage = st.selectbox(
            "Current Stage",
            [
                "Idea",
                "Pre-MVP",
                "MVP",
                "Early Revenue",
                "Growth",
                "Established Business"
            ]
        )

        geography = st.text_input(
            "Target Geography",
            placeholder="e.g. South Africa, UK, Global"
        )

    with col2:

        target_customer = st.text_area(
            "Target Customer",
            placeholder="Who buys or uses the solution?",
            height=118
        )

        revenue_model = st.text_input(
            "Revenue Model",
            placeholder="SaaS, licensing, consulting, transaction fee..."
        )

        primary_goal = st.selectbox(
            "Primary Decision",
            [
                "Strongest market opportunity",
                "Product differentiation",
                "Best target market",
                "MVP definition",
                "Commercial viability",
                "Go-to-market direction"
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

    submit = st.form_submit_button(
        "Generate Venture Intelligence Report"
    )

# =========================================================
# INTELLIGENCE PROMPT
# =========================================================

def create_analysis_prompt():

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

Target geography:
{geography}

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

Constraints:
{constraints}


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


9. FINAL DECISION BRIEF

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
"""

# =========================================================
# RUN ENGINE
# =========================================================

if submit:

    if not OPENAI_API_KEY:

        st.error(
            "OPENAI_API_KEY was not found in the project .env file."
        )

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

                report = response.output_text

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
                    }
                )


                status.update(
                    label="Venture Intelligence analysis complete",
                    state="complete"
                )

                st.markdown(
                    report
                )

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
                        company_name=company_name.strip()
                        if company_name else None
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
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Venture Navigator AI • Powered by AI Catalyst Studio • Beta"
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
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 750 !important;
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

