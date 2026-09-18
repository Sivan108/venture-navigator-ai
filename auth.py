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
/* AUTH LABEL CONTRAST FIX */

<style>

div[data-testid="stTabs"] label,
div[data-testid="stTabs"] p,
div[data-testid="stForm"] label,
div[data-testid="stWidgetLabel"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

</style>

<style>

.vn-auth-shell {
    max-width: 720px;
    margin: 2rem auto;
}

.vn-auth-badge {
    display: inline-block;
    padding: 0.38rem 0.72rem;
    border-radius: 999px;
    background: linear-gradient(90deg, #0f4969, #1f78a7);
    color: white !important;
    font-weight: 750;
    font-size: 0.82rem;
    margin-bottom: 0.8rem;
}

.vn-auth-title {
    color: #153b55 !important;
    font-size: 2.5rem;
    font-weight: 850;
    line-height: 1.05;
    margin-bottom: 0.5rem;
}

.vn-auth-copy {
    color: #35556b !important;
    margin-bottom: 1.2rem;
}

.vn-beta-bar {
    box-sizing: border-box;
    width: 100%;
    margin: 0 0 1rem 0;
    padding: 0.65rem 0.9rem;
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


# =========================================================
# DATE HELPERS
# =========================================================

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

def auth_screen():

    st.markdown(AUTH_STYLE, unsafe_allow_html=True)

    st.markdown(
        '<div class="vn-auth-badge">BETA • 7 DAYS FREE</div>',
        unsafe_allow_html=True
    )

    st.title("Venture Navigator AI")

    st.markdown(
        "**Register for beta access or sign in to continue.**"
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
                "I understand that Venture Navigator AI is currently a beta version."
            )

            register_clicked = st.form_submit_button(
                "Start my 7-day free beta",
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

                        st.success(
                            "Welcome to Venture Navigator AI. "
                            "Your 7-day beta has started."
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
    # 7-DAY BETA
    # -----------------------------------------------------

    created_at = normalise_datetime(
        user.created_at
    )

    trial_end = created_at + timedelta(
        days=BETA_DAYS
    )

    now = datetime.now(timezone.utc)

    remaining = trial_end - now

    if remaining.total_seconds() <= 0:

        st.error(
            "Your 7-day Venture Navigator AI beta has ended."
        )

        st.markdown(
            """
            Contact **AI Catalyst Studio** if you would like
            continued access to Venture Navigator AI.
            """
        )

        if st.button(
            "Log out",
            key="vn_expired_logout",
            use_container_width=True
        ):
            logout()

        st.stop()

    days_remaining = max(
        1,
        math.ceil(
            remaining.total_seconds() / 86400
        )
    )

    expiry = trial_end.strftime(
        "%d %b %Y"
    )

    left, right = st.columns([8, 1.3])

    with left:

        st.markdown(
            f"""
            <div class="vn-beta-bar">
                <strong>VENTURE NAVIGATOR AI • BETA</strong>
                &nbsp;&nbsp;•&nbsp;&nbsp;
                {days_remaining} day{"s" if days_remaining != 1 else ""} remaining
                &nbsp;&nbsp;•&nbsp;&nbsp;
                Ends {expiry}
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

    return {
        "user": user,
        "is_admin": False,
        "days_remaining": days_remaining,
        "trial_end": trial_end,
    }
