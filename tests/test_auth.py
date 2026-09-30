"""Google sign-in gate.

AppTest runs dashboard.py in this process, so patching app.auth's helpers
stands in for Google and the secrets file.
"""

import pytest
from streamlit.testing.v1 import AppTest

import app.auth as auth
from app.auth import is_email_allowed

USER = {"name": "Test User", "email": "tester@example.com", "email_verified": True}


def _patch(monkeypatch, *, configured=True, logged_in=True, user=USER, access=None):
    monkeypatch.setattr(auth, "auth_configured", lambda: configured)
    monkeypatch.setattr(auth, "_is_logged_in", lambda: logged_in)
    monkeypatch.setattr(auth, "_user_info", lambda: dict(user))
    monkeypatch.setattr(
        auth, "_secrets_section", lambda name: (access or {}) if name == "access" else {}
    )


@pytest.fixture(autouse=True, scope="module")
def signed_in():
    """Default for dashboard tests: an allowed user is signed in."""
    mp = pytest.MonkeyPatch()
    _patch(mp)
    yield
    mp.undo()


def run_app():
    app = AppTest.from_file("dashboard.py", default_timeout=120)
    app.run()
    return app


class TestEmailRule:
    def test_any_verified_account_when_no_allowlist(self):
        assert is_email_allowed("a@gmail.com", True)

    def test_unverified_email_rejected(self):
        assert not is_email_allowed("a@gmail.com", False)

    def test_missing_email_rejected(self):
        assert not is_email_allowed(None, True)

    def test_allowlisted_email(self):
        assert is_email_allowed("Me@Gmail.com", True, allowed_emails=["me@gmail.com"])
        assert not is_email_allowed("other@gmail.com", True, allowed_emails=["me@gmail.com"])

    def test_allowlisted_domain(self):
        assert is_email_allowed("prof@college.edu", True, allowed_domains=["college.edu"])
        assert not is_email_allowed("x@evil-college.edu", True, allowed_domains=["college.edu"])


class TestGate:
    def test_not_configured_fails_closed(self, monkeypatch):
        _patch(monkeypatch, configured=False, logged_in=True)
        app = run_app()
        assert not app.exception
        assert "not been set up" in " ".join(e.value for e in app.error)
        assert not app.text_area  # the screening UI never rendered

    def test_signed_out_sees_only_login(self, monkeypatch):
        _patch(monkeypatch, logged_in=False)
        app = run_app()
        assert not app.exception
        assert [b.label for b in app.button] == ["Continue with Google"]
        assert not app.text_area

    def test_disallowed_account_is_denied(self, monkeypatch):
        _patch(monkeypatch, access={"allowed_emails": ["boss@example.com"]})
        app = run_app()
        assert not app.exception
        assert "not on the access list" in " ".join(e.value for e in app.error)
        assert not app.text_area

    def test_allowed_user_gets_the_app(self, monkeypatch):
        _patch(monkeypatch)
        app = run_app()
        assert not app.exception
        assert app.text_area[0].label == "Job description"
        assert "Sign out" in [b.label for b in app.button]
