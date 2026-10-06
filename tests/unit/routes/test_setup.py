from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from database.models import Client, SetupSession
from main import app
from routes.templates import COOKIE, digest
from utils.config import settings

BASE = "https://connect.squareupsandbox.com"


@pytest.fixture
def browser(session_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "APP_URL", "https://localhost:8000")
    monkeypatch.setattr(settings, "LOG_DIR", tmp_path)
    with TestClient(app, base_url=settings.APP_URL, follow_redirects=False) as client:
        yield client


def begin(browser):
    response = browser.get("/auth/square")
    assert response.status_code == 303
    return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]


def mock_oauth(merchant="merchant-1", access="new-token"):
    token = respx.post(f"{BASE}/oauth2/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "merchant_id": merchant,
                "access_token": access,
                "refresh_token": "new-refresh",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )
    )
    respx.get(f"{BASE}/v2/merchants/{merchant}").mock(
        return_value=httpx.Response(200, json={"merchant": {"business_name": "Cafe"}})
    )
    return token


def authorized(browser, db):
    state = begin(browser)
    mock_oauth()
    assert (
        browser.get(
            "/square-auth/callback", params={"state": state, "code": "one-use-code"}
        ).status_code
        == 303
    )
    session = db.get(SetupSession, digest(browser.cookies.get(COOKIE)))
    return session.csrf_token


@respx.mock
async def test_new_merchant_setup_is_bound_one_use_and_cookie_secure(browser, db):
    state = begin(browser)
    first_cookie = browser.cookies.get(COOKIE)
    token = mock_oauth()
    response = browser.get("/square-auth/callback", params={"state": state, "code": "code"})
    assert response.status_code == 303
    assert browser.cookies.get(COOKIE) != first_cookie
    assert "Secure" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert token.call_count == 1
    session = db.get(SetupSession, digest(browser.cookies.get(COOKIE)))
    csrf = session.csrf_token
    page = browser.get("/")
    assert "Cafe" in page.text and "csrf_token" in page.text
    assert 'name="client_id"' not in page.text
    assert page.headers["cache-control"] == "no-store"
    assert "script-src 'none'" in page.headers["content-security-policy"]
    route = respx.get("https://partner.combohr.com/api/v1/locations").mock(
        return_value=httpx.Response(200, json=[{"id": "combo"}])
    )
    submitted = browser.post(
        "/combo", data={"api_key": "key", "csrf_token": csrf}, headers={"Origin": settings.APP_URL}
    )
    assert submitted.status_code == 303
    assert not browser.cookies.get(COOKIE)
    assert route.call_count == 1
    assert db.query(Client).one().combo_api_key == "key"
    assert (
        browser.post(
            "/combo",
            data={"api_key": "other", "csrf_token": csrf},
            headers={"Origin": settings.APP_URL},
        ).status_code
        == 403
    )


@pytest.mark.parametrize("state", [None, "wrong"])
@respx.mock
async def test_invalid_oauth_state_makes_no_exchange(browser, state):
    begin(browser)
    response = browser.get(
        "/square-auth/callback", params={"code": "code", **({"state": state} if state else {})}
    )
    assert response.status_code == 403
    assert len(respx.calls) == 0


@respx.mock
async def test_expired_cross_browser_and_replayed_state(browser, db):
    state = begin(browser)
    with TestClient(app, base_url=settings.APP_URL) as other:
        assert (
            other.get("/square-auth/callback", params={"code": "code", "state": state}).status_code
            == 403
        )
    session = db.get(SetupSession, digest(browser.cookies.get(COOKIE)))
    session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db.commit()
    assert (
        browser.get("/square-auth/callback", params={"code": "code", "state": state}).status_code
        == 403
    )
    assert len(respx.calls) == 0
    state = begin(browser)
    token = mock_oauth()
    assert (
        browser.get("/square-auth/callback", params={"code": "code", "state": state}).status_code
        == 303
    )
    assert (
        browser.get("/square-auth/callback", params={"code": "code", "state": state}).status_code
        == 403
    )
    assert token.call_count == 1


@respx.mock
async def test_reconnect_refreshes_revoked_tokens_without_replacing_combo(
    browser, db, client_record
):
    client_record.combo_api_key = "existing"
    client_record.square_access_token_revoked = True
    client_record.is_active = False
    db.commit()
    state = begin(browser)
    mock_oauth(access="fresh")
    assert (
        browser.get("/square-auth/callback", params={"code": "code", "state": state}).status_code
        == 303
    )
    db.expire_all()
    assert client_record.square_access_token == "fresh"
    assert client_record.square_refresh_token == "new-refresh"
    assert not client_record.square_access_token_revoked
    assert not client_record.is_active
    assert client_record.combo_api_key == "existing"
    assert (
        browser.post(
            "/combo",
            data={"api_key": "replacement", "csrf_token": "guess"},
            headers={"Origin": settings.APP_URL},
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("anonymous", 403),
        ("preoauth", 403),
        ("expired", 403),
        ("badcsrf", 403),
        ("foreign", 403),
        ("missingorigin", 403),
        ("clientid", 400),
        ("multipart", 415),
        ("missingclient", 409),
    ],
)
@respx.mock
async def test_unauthorized_writes_make_no_combo_call(browser, db, client_record, mode, expected):
    if mode == "anonymous":
        csrf = "guess"
    elif mode == "preoauth":
        begin(browser)
        csrf = "guess"
    else:
        csrf = authorized(browser, db)
    respx.calls.clear()
    data = {"api_key": "attacker-key", "csrf_token": csrf}
    headers = {"Origin": settings.APP_URL}
    if mode == "badcsrf":
        data["csrf_token"] = "wrong"
    if mode == "foreign":
        headers["Origin"] = "https://attacker.example"
    if mode == "missingorigin":
        headers.clear()
    if mode == "clientid":
        data["client_id"] = str(client_record.id)
    if mode == "expired":
        db.get(SetupSession, digest(browser.cookies.get(COOKIE))).expires_at = datetime.now(
            UTC
        ).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
    if mode == "missingclient":
        db.delete(client_record)
        db.commit()
    response = browser.post(
        "/combo",
        data=data,
        headers=headers,
        **({"files": {"extra": (None, "x")}} if mode == "multipart" else {}),
    )
    assert response.status_code == expected
    assert len(respx.calls) == 0
    db.expire_all()
    assert not db.query(Client).filter(Client.combo_api_key.isnot(None)).count()


@respx.mock
async def test_invalid_combo_key_can_retry_and_never_logs_key(browser, db, caplog):
    csrf = authorized(browser, db)
    combo = respx.get("https://partner.combohr.com/api/v1/locations").mock(
        return_value=httpx.Response(401)
    )
    data = {"api_key": "PRIVATE_COMBO_SENTINEL", "csrf_token": csrf}
    assert (
        browser.post("/combo", data=data, headers={"Origin": settings.APP_URL}).headers["location"]
        == "/?status=invalid-key"
    )
    assert browser.cookies.get(COOKIE)
    assert "PRIVATE_COMBO_SENTINEL" not in caplog.text
    combo.mock(return_value=httpx.Response(200, json=[{"id": "valid"}]))
    assert (
        browser.post("/combo", data=data, headers={"Origin": settings.APP_URL}).status_code == 303
    )
    assert db.query(Client).one().combo_api_key == "PRIVATE_COMBO_SENTINEL"


@respx.mock
async def test_consumed_state_stays_consumed_after_provider_failure(browser):
    state = begin(browser)
    token = respx.post(f"{BASE}/oauth2/token").mock(return_value=httpx.Response(500))
    response = browser.get("/square-auth/callback", params={"state": state, "code": "secret-code"})
    assert response.status_code == 502
    assert (
        browser.get(
            "/square-auth/callback", params={"state": state, "code": "secret-code"}
        ).status_code
        == 403
    )
    assert token.call_count == 1


async def test_body_cap_host_and_removed_placeholders(browser):
    assert browser.post("/combo", content=b"x" * 16385).status_code == 413
    assert browser.get("/", headers={"Host": "attacker.example"}).status_code == 400
    assert browser.get("/admin/clients").status_code == 404
    assert browser.post("/auth/clients", json={}).status_code == 404
    assert browser.get("/static/template.js").status_code == 404


async def test_unconfigured_onboarding_and_new_attempt_invalidates_old(browser, db, monkeypatch):
    first = begin(browser)
    second = begin(browser)
    assert first != second
    assert db.query(SetupSession).count() == 1
    assert (
        browser.get("/square-auth/callback", params={"state": first, "code": "code"}).status_code
        == 403
    )
    monkeypatch.setattr(settings, "SQUARE_CLIENT_ID", "")
    assert browser.get("/auth/square").status_code == 503
