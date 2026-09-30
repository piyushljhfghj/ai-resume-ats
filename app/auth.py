# app/auth.py
"""Google sign-in gate for the dashboard.

Uses Streamlit's built-in OpenID Connect support (st.login / st.user /
st.logout), so no password is ever stored or seen by this app: Google
authenticates the user and Streamlit keeps the identity in a signed,
HTTP-only cookie.

Configuration lives in .streamlit/secrets.toml (see secrets.toml.example):

    [auth]              redirect_uri, cookie_secret
    [auth.google]       client_id, client_secret, server_metadata_url
    [access]            optional allowed_emails / allowed_domains

The gate fails closed: if [auth.google] is missing, the app refuses to
run rather than silently serving everyone.
"""

import streamlit as st

from app.ui_theme import hero_html

PROVIDER = "google"


def _secrets_section(name):
    """A top-level secrets table, or {} when there is no secrets file."""
    try:
        return st.secrets.get(name, {}) or {}
    except Exception:
        return {}


def auth_configured():
    auth = _secrets_section("auth")
    google = auth.get(PROVIDER, {}) if hasattr(auth, "get") else {}
    required = (auth.get("redirect_uri"), auth.get("cookie_secret"),
                google.get("client_id"), google.get("client_secret"))
    return all(required) and not any("REPLACE" in str(v) for v in required)


def _normalise(values):
    return {str(v).strip().lower() for v in (values or []) if str(v).strip()}


def is_email_allowed(email, email_verified, allowed_emails=(), allowed_domains=()):
    """Access rule, kept pure so it can be unit tested.

    * The email must be present and verified by Google.
    * With no allowlist configured, any verified Google account may enter.
    * Otherwise the address must be listed, or its domain must be.
    """
    if not email or not email_verified:
        return False
    email = email.strip().lower()
    emails, domains = _normalise(allowed_emails), _normalise(allowed_domains)
    if not emails and not domains:
        return True
    return email in emails or email.rsplit("@", 1)[-1] in domains


def _is_logged_in():
    return bool(getattr(st.user, "is_logged_in", False))


def _user_info():
    return {
        "name": st.user.get("name"),
        "email": st.user.get("email"),
        "email_verified": st.user.get("email_verified", False),
    }


def sign_out():
    # Drop this session's screening data before the identity goes, so the
    # next person on this browser cannot see it.
    st.session_state.clear()
    st.logout()


def _setup_required():
    st.markdown(
        hero_html("Sign-in not configured", "The screening app is locked."),
        unsafe_allow_html=True,
    )
    st.error(
        "Google sign-in has not been set up, so the app will not open. Add an "
        "`[auth]` and `[auth.google]` section to `.streamlit/secrets.toml` "
        "(locally) or to the app's Secrets (Streamlit Cloud). See "
        "`.streamlit/secrets.toml.example`.",
        icon=":material/lock:",
    )
    st.stop()


def _login_page():
    st.markdown(
        hero_html(
            "Resume Screening",
            "Sign in to rank candidates against a role, with the reasoning shown.",
        ),
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 2, 1])
    with mid, st.container(border=True):
        st.markdown("##### Sign in")
        st.caption(
            "Use your Google account. New users are signed up automatically "
            "on first sign-in; this app never sees your password."
        )
        st.button(
            "Continue with Google",
            type="primary",
            width="stretch",
            icon=":material/login:",
            on_click=st.login,
            args=(PROVIDER,),
        )
    st.stop()


def _access_denied(email):
    st.markdown(
        hero_html("Access denied", "This account is not allowed to use the app."),
        unsafe_allow_html=True,
    )
    st.error(
        f"`{email or 'unknown'}` is not on the access list, or "
        "its email address is not verified by Google. Ask the administrator "
        "to add it, or sign in with a different account.",
        icon=":material/block:",
    )
    st.button("Sign out", on_click=sign_out, icon=":material/logout:")
    st.stop()


def require_login():
    """Stop the script unless an allowed Google user is signed in.

    Returns {"name", "email", "email_verified"} for the signed-in user.
    """
    if not auth_configured():
        _setup_required()
    if not _is_logged_in():
        _login_page()

    user = _user_info()
    access = _secrets_section("access")
    if not is_email_allowed(
        user["email"],
        user["email_verified"],
        access.get("allowed_emails", []),
        access.get("allowed_domains", []),
    ):
        _access_denied(user["email"])
    return user
