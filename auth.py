import os
from pathlib import Path
import math
from datetime import datetime, timedelta, timezone

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client



# =========================================================
# LOAD PROJECT ENVIRONMENT
# =========================================================

ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=False)

# =========================================================
# SETTINGS
# =========================================================

def get_setting(name, default=None):
    """
    Configuration priority:
    1. Streamlit Cloud secrets
    2. Environment variables
    3. Default
    """

    # Production: Streamlit Community Cloud
    try:
        if name in st.secrets:
            value = st.secrets[name]
            if value is not None and str(value).strip():
                return str(value).strip()
    except Exception:
        pass

    # Local development: .env / environment variables
    value = os.getenv(name)

    if value is not None and str(value).strip():
        return str(value).strip()

    return default


BETA_DAYS = int(get_setting("BETA_DAYS", "7"))

ADMIN_EMAILS = {
    email.strip().lower()
    for email in str(get_setting("ADMIN_EMAILS", "")).split(",")
    if email.strip()
}


# =========================================================
# AUTH STYLING
# =========================================================

AUTH_STYLE = """
<style>

/* ======================================================
   AUTH PAGE
====================================================== */

.vn-auth-shell {
    max-width: 1100px;
    margin: 2rem auto;
}

'<div class="vn-auth-badge">BETA ACCESS</div>',
    display: inline-block;
    padding: 0.42rem 0.78rem;
    border-radius: 999px;
    background: linear-gradient(90deg, #0f4969, #1f78a7);
    color: #ffffff !important;
    font-weight: 800;
    font-size: 0.84rem;
    margin-bottom: 0.9rem;
}

.vn-auth-title {
    font-size: 3.2rem;
    line-height: 1.05;
    font-weight: 850;
    color: #163c57 !important;
    margin-bottom: 0.65rem;
}

.vn-auth-copy {
    font-size: 1.05rem;
    font-weight: 650;
    color: #173e58 !important;
    margin-bottom: 1.25rem;
}


/* ======================================================
   TABS ON SILVER BACKGROUND
====================================================== */

div[data-testid="stTabs"] button {
    color: #173e58 !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
}

div[data-testid="stTabs"] button p,
div[data-testid="stTabs"] button span {
    color: #173e58 !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #0c5677 !important;
}


/* ======================================================
   AUTH FORM PANEL
====================================================== */

div[data-testid="stTabs"] div[data-testid="stForm"] {
    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,0.98) 0%,
            rgba(233,239,244,0.98) 100%
        ) !important;

    border: 1px solid rgba(33, 122, 154, 0.24) !important;
    border-radius: 20px !important;
    padding: 1.8rem !important;

    box-shadow:
        0 16px 34px rgba(40, 67, 83, 0.12) !important;
}


/* ======================================================
   LABELS — WHITE ON NAVY
====================================================== */

div[data-testid="stTabs"] div[data-testid="stForm"] label,
div[data-testid="stTabs"] div[data-testid="stForm"] [data-testid="stWidgetLabel"] p,
div[data-testid="stTabs"] div[data-testid="stForm"] .stCheckbox p {
    color: #173e58 !important;
    -webkit-text-fill-color: #173e58 !important;
    font-weight: 750 !important;
}


/* ======================================================
   INPUTS — LIGHT BACKGROUND / DARK TEXT
====================================================== */

div[data-testid="stTabs"] div[data-testid="stForm"] [data-baseweb="input"] > div,
div[data-testid="stTabs"] div[data-testid="stForm"] [data-baseweb="textarea"] > div,
div[data-testid="stTabs"] div[data-testid="stForm"] [data-baseweb="select"] > div {
    background: #f3f8fc !important;
    border: 1px solid #8cddec !important;
    border-radius: 12px !important;
}

div[data-testid="stTabs"] div[data-testid="stForm"] input,
div[data-testid="stTabs"] div[data-testid="stForm"] textarea {
    color: #143a50 !important;
    -webkit-text-fill-color: #143a50 !important;
    font-weight: 650 !important;
    background: transparent !important;
}

div[data-testid="stTabs"] div[data-testid="stForm"] input::placeholder,
div[data-testid="stTabs"] div[data-testid="stForm"] textarea::placeholder {
    color: #718da0 !important;
    -webkit-text-fill-color: #718da0 !important;
    opacity: 1 !important;
}


/* Password eye icon */
div[data-testid="stTabs"] div[data-testid="stForm"] svg {
    color: #173e58 !important;
    fill: #173e58 !important;
}


/* ======================================================
   CHECKBOX
====================================================== */

div[data-testid="stTabs"] div[data-testid="stForm"] .stCheckbox label,
div[data-testid="stTabs"] div[data-testid="stForm"] .stCheckbox label span,
div[data-testid="stTabs"] div[data-testid="stForm"] .stCheckbox label p {
    color: #173e58 !important;
    -webkit-text-fill-color: #173e58 !important;
    font-weight: 750 !important;
}


/* ======================================================
   AUTH BUTTON
====================================================== */

div[data-testid="stTabs"] div[data-testid="stForm"] .stFormSubmitButton button {
    width: 100% !important;
    min-height: 3.5rem !important;

    border-radius: 13px !important;
    border: 1px solid rgba(255,255,255,0.30) !important;

    background:
        linear-gradient(
            95deg,
            #2dc8d8 0%,
            #1da8df 48%,
            #3578e5 100%
        ) !important;

    color: #ffffff !important;

    font-size: 1rem !important;
    font-weight: 850 !important;

    box-shadow:
        0 12px 28px rgba(18, 112, 188, 0.28) !important;
}

div[data-testid="stTabs"] div[data-testid="stForm"] .stFormSubmitButton button p,
div[data-testid="stTabs"] div[data-testid="stForm"] .stFormSubmitButton button span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}


/* ======================================================
   AUTH TRUST PANEL
====================================================== */

.vn-auth-trust {
    background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(230,239,244,0.94));
    border: 1px solid rgba(20, 156, 190, 0.26);
    border-left: 4px solid #20b9d7;
    border-radius: 13px;
    padding: 0.9rem 1rem;
    margin: 0.8rem 0 1.15rem 0;
    color: #244d62 !important;
    font-size: 0.94rem;
    line-height: 1.45;
}
.vn-auth-trust strong { color: #153b55 !important; }

/* ======================================================
   BETA BAR AFTER LOGIN
====================================================== */

.vn-beta-bar {
    box-sizing: border-box;
    width: 100%;
    margin: 0 0 1rem 0;
    padding: 0.7rem 1rem;
    border-radius: 10px;

    background:
        linear-gradient(
            95deg,
            #0b3149 0%,
            #125675 52%,
            #1d81ae 100%
        );

    border: 1px solid rgba(49, 210, 232, 0.35);

    box-shadow:
        0 8px 20px rgba(27, 75, 104, 0.16);
}

.vn-beta-bar,
.vn-beta-bar span,
.vn-beta-bar strong {
    color: #ffffff !important;
}

</style>
"""



# =========================================================
# AUTH INPUT CONTRAST — FINAL NARROW OVERRIDE
# =========================================================

AUTH_INPUT_FIX = """
<style>

/* Only affect Login / Create Account forms */

[data-testid="stTabs"] [data-testid="stForm"]
div[data-baseweb="input"] > div,

[data-testid="stTabs"] [data-testid="stForm"]
div[data-baseweb="textarea"] > div {

    background: #f4f7fb !important;
    background-color: #f4f7fb !important;

    border: 1px solid #83d8e8 !important;
    border-radius: 11px !important;
}


/* Actual typed text */

[data-testid="stTabs"] [data-testid="stForm"] input,
[data-testid="stTabs"] [data-testid="stForm"] textarea {

    background: #f4f7fb !important;
    background-color: #f4f7fb !important;

    color: #15384d !important;
    -webkit-text-fill-color: #15384d !important;

    caret-color: #15384d !important;

    font-weight: 600 !important;
}


/* Placeholder text */

[data-testid="stTabs"] [data-testid="stForm"] input::placeholder,
[data-testid="stTabs"] [data-testid="stForm"] textarea::placeholder {

    color: #718b9c !important;
    -webkit-text-fill-color: #718b9c !important;

    opacity: 1 !important;
}


/* Chrome / Safari autofill */

[data-testid="stTabs"] [data-testid="stForm"]
input:-webkit-autofill,

[data-testid="stTabs"] [data-testid="stForm"]
input:-webkit-autofill:hover,

[data-testid="stTabs"] [data-testid="stForm"]
input:-webkit-autofill:focus {

    -webkit-text-fill-color: #15384d !important;

    -webkit-box-shadow:
        0 0 0 1000px #f4f7fb inset !important;

    box-shadow:
        0 0 0 1000px #f4f7fb inset !important;
}


/* Password eye icon */

[data-testid="stTabs"] [data-testid="stForm"]
div[data-baseweb="input"] svg {

    color: #15384d !important;
    fill: #15384d !important;
}


/* Labels remain white against blue auth panel */

[data-testid="stTabs"] [data-testid="stForm"]
[data-testid="stWidgetLabel"] p,

[data-testid="stTabs"] [data-testid="stForm"] label {

    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;

    font-weight: 700 !important;
}

</style>
"""

# =========================================================
# SUPABASE
# =========================================================

def get_supabase():
    # Read configuration at runtime so Streamlit Cloud secrets
    # are guaranteed to be available.

    supabase_url = get_setting("SUPABASE_URL")
    supabase_key = get_setting("SUPABASE_PUBLISHABLE_KEY")

    if not supabase_url:
        st.error(
            "SUPABASE_URL is missing from the application configuration."
        )
        st.stop()

    if not supabase_key:
        st.error(
            "SUPABASE_PUBLISHABLE_KEY is missing from the application configuration."
        )
        st.stop()

    if "vn_supabase_client" not in st.session_state:
        st.session_state.vn_supabase_client = create_client(
            supabase_url,
            supabase_key
        )

    return st.session_state.vn_supabase_client


def get_supabase_admin():
    supabase_url = get_setting("SUPABASE_URL")
    supabase_secret_key = get_setting("SUPABASE_SECRET_KEY")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is missing.")

    if not supabase_secret_key:
        raise RuntimeError("SUPABASE_SECRET_KEY is missing.")

    return create_client(
        supabase_url,
        supabase_secret_key
    )

def normalise_datetime(value):

    if isinstance(value, datetime):
        dt = value

    else:
        value = str(value)

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# =========================================================
# AUTH SCREEN
# =========================================================


# =========================================================
# USAGE TRACKING
# =========================================================
def track_usage_event(
    event_type,
    user=None,
    venture_name=None,
    venture_stage=None,
    primary_goal=None,
    metadata=None,
):
    """
    Record Venture Navigator beta activity.
    Tracking failures must never interrupt the user experience.
    """
    try:
        if user is None:
            user = st.session_state.get("vn_user")

        if user is None:
            return

        user_id = str(user.id)
        user_email = (user.email or "").strip().lower()

        get_supabase().table("venture_usage_events").insert({
            "user_id": user_id,
            "user_email": user_email,
            "event_type": event_type,
            "venture_name": venture_name,
            "venture_stage": venture_stage,
            "primary_goal": primary_goal,
            "metadata": metadata or {},
        }).execute()

        if event_type in {"login", "signup"}:
            get_supabase().table("venture_beta_users").update({
                "last_login_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).execute()

    except Exception:
        # Analytics must never interrupt the live application.
        pass


def auth_screen():

    st.markdown(AUTH_STYLE, unsafe_allow_html=True)
    st.markdown(AUTH_INPUT_FIX, unsafe_allow_html=True)

    if Path("VN_Logo_Horizontal.png").exists():
        st.image("VN_Logo_Horizontal.png", use_container_width=True)
    elif Path("VN_Logo_Horizontal.png").exists():
        st.image("VN_Logo_Horizontal.png", use_container_width=True)
    elif Path("VN_Icon.png").exists():
        st.image("VN_Icon.png", width=180)

    st.markdown(
        '<div class="vn-auth-badge">BETA ACCESS</div>',
        unsafe_allow_html=True
    )

    st.title("Venture Navigator AI")

    st.markdown(
        "**AI-powered venture intelligence by AI Catalyst Studio.** "
        "Sign in or create an account to continue."
    )

    st.markdown(
        """
        <div class="vn-auth-trust">
            <strong>🔒 Your venture ideas remain yours.</strong><br/>
            Your venture information is treated as confidential. AI Catalyst Studio does not use
            submitted venture ideas to develop competing products or commercial opportunities.
            Venture content is processed only to provide the Venture Navigator service.
        </div>
        """,
        unsafe_allow_html=True
    )

    login_tab, register_tab = st.tabs(
        ["Log in", "Create account"]
    )

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    with login_tab:

        with st.form("vn_login_form"):

            email = st.text_input(
                "Email address",
                key="vn_login_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="vn_login_password"
            )

            login_clicked = st.form_submit_button(
                "Log in",
                use_container_width=True
            )

        if login_clicked:

            if not email or not password:

                st.warning(
                    "Enter your email address and password."
                )

            else:

                try:

                    response = get_supabase().auth.sign_in_with_password(
                        {
                            "email": email.strip(),
                            "password": password,
                        }
                    )

                    if response.user:

                        st.session_state.vn_user = response.user
                        st.rerun()

                except Exception as exc:

                    st.error(
                        f"Login failed: {exc}"
                    )

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    with register_tab:

        with st.form("vn_registration_form"):

            full_name = st.text_input(
                "Name",
                key="vn_register_name"
            )

            email = st.text_input(
                "Email address",
                key="vn_register_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="vn_register_password"
            )

            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="vn_register_confirm"
            )

            beta_acknowledgement = st.checkbox(
                "I understand that Venture Navigator AI is currently in beta."
            )

            register_clicked = st.form_submit_button(
                "Create my account",
                use_container_width=True
            )

        if register_clicked:

            if not full_name.strip():

                st.warning("Enter your name.")

            elif not email.strip():

                st.warning("Enter your email address.")

            elif len(password) < 8:

                st.warning(
                    "Use a password containing at least 8 characters."
                )

            elif password != confirm_password:

                st.warning(
                    "The two passwords do not match."
                )

            elif not beta_acknowledgement:

                st.warning(
                    "Please acknowledge that this is a beta version."
                )

            else:

                try:

                    response = get_supabase().auth.sign_up(
                        {
                            "email": email.strip(),
                            "password": password,
                            "options": {
                                "data": {
                                    "full_name": full_name.strip()
                                }
                            }
                        }
                    )

                    if response.session and response.user:
                        st.session_state.vn_user = response.user
                        track_usage_event(
                            "signup",
                            user=response.user,
                            metadata={"full_name": full_name.strip()}
                        )
                        st.success(
                            "Welcome to Venture Navigator AI. "
                            "Your Venture Navigator AI access is active."
                        )

                        st.rerun()

                    else:

                        st.success(
                            "Your account has been created. "
                            "Check your email if Supabase requests confirmation."
                        )

                except Exception as exc:

                    st.error(
                        f"Registration failed: {exc}"
                    )


# =========================================================
# LOGOUT
# =========================================================

def delete_current_account(user):
    """
    Permanently delete the signed-in Venture Navigator account
    and associated Venture Navigator usage records.
    """

    user_id = str(user.id)

    admin = get_supabase_admin()

    admin.table("venture_usage_events").delete().eq(
        "user_id", user_id
    ).execute()

    admin.table("venture_beta_users").delete().eq(
        "user_id", user_id
    ).execute()

    admin.auth.admin.delete_user(user_id)

    st.session_state.pop("vn_user", None)


def logout():

    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass

    st.session_state.pop("vn_user", None)

    st.rerun()


# =========================================================
# BETA ACCESS GATE
# =========================================================

def require_beta_access():

    st.markdown(AUTH_STYLE, unsafe_allow_html=True)

    user = st.session_state.get("vn_user")

    if user is None:

        try:

            result = get_supabase().auth.get_user()

            if result and result.user:
                user = result.user
                st.session_state.vn_user = user

        except Exception:
            user = None

    if user is None:

        auth_screen()
        st.stop()

    user_email = (user.email or "").strip().lower()

    # -----------------------------------------------------
    # ADMIN ACCESS DOES NOT EXPIRE
    # -----------------------------------------------------

    if user_email in ADMIN_EMAILS:

        left, right = st.columns([8, 1.3])

        with left:

            st.markdown(
                f"""
                <div class="vn-beta-bar">
                    <strong>VENTURE NAVIGATOR AI • BETA ADMIN</strong>
                    &nbsp;&nbsp;•&nbsp;&nbsp;
                    {user.email}
                </div>
                """,
                unsafe_allow_html=True
            )

        with right:

            if st.button(
                "Log out",
                key="vn_admin_logout",
                use_container_width=True
            ):
                logout()

        return {
            "user": user,
            "is_admin": True,
            "days_remaining": None,
        }

    # -----------------------------------------------------
    # BETA ACCESS
    # -----------------------------------------------------


    days_remaining = None
    expiry = None

    left, right = st.columns([8, 1.3])

    with left:

        st.markdown(
            f"""
            <div class="vn-beta-bar">
                <strong>VENTURE NAVIGATOR AI • BETA</strong>
                &nbsp;&nbsp;•&nbsp;&nbsp;
                &nbsp;&nbsp;•&nbsp;&nbsp;
                &nbsp;&nbsp;•&nbsp;&nbsp;
                {user.email}
            </div>
            """,
            unsafe_allow_html=True
        )

    with right:

        if st.button(
            "Log out",
            key="vn_beta_logout",
            use_container_width=True
        ):
            logout()

    with st.expander("Account settings"):

        st.markdown("### Delete account")

        st.warning(
            "Deleting your account is permanent. "
            "Your Venture Navigator account and associated usage records "
            "will be removed and cannot be restored."
        )

        confirm_delete = st.checkbox(
            "I understand that this permanently deletes my account.",
            key="vn_confirm_delete"
        )

        if st.button(
            "Delete my account",
            key="vn_delete_account",
            type="primary",
            disabled=not confirm_delete
        ):

            try:
                delete_current_account(user)

                st.success(
                    "Your Venture Navigator account has been deleted."
                )

                st.session_state.clear()
                st.rerun()

            except Exception:
                st.error(
                    "We could not delete your account. "
                    "Please try again or contact AI Catalyst Studio."
                )

    return {
        "user": user,
        "is_admin": False,
        "days_remaining": None,
        "trial_end": None,
    }
