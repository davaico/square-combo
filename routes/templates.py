"""Browser-bound, one-use setup capabilities; no client IDs come from forms."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from adapters.combo.client import ComboClient
from adapters.square.client import SquareClient
from database.database import get_db
from database.models import Client, SetupSession
from services.client_service import ClientService
from services.setup_service import SetupService
from utils.config import BASE_DIR, settings
from utils.http import safe_error

router = APIRouter()
templates = Jinja2Templates(directory=BASE_DIR / "templates")
logger = logging.getLogger(__name__)
COOKIE = "square_combo_setup"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_session(request: Request, db: Session) -> SetupSession:
    token = request.cookies.get(COOKIE)
    session = db.get(SetupSession, digest(token)) if token else None
    if session is None or session.expires_at <= now():
        raise HTTPException(403, "Setup expired. Connect Square again.")
    return session


def set_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.SETUP_TTL_SECONDS,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def finished() -> RedirectResponse:
    response = RedirectResponse("/?status=connected", status_code=303)
    response.delete_cookie(
        COOKIE, path="/", secure=settings.secure_cookies, httponly=True, samesite="lax"
    )
    return response


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    session = None
    try:
        session = get_session(request, db)
    except HTTPException:
        pass
    client = db.get(Client, session.client_id) if session and session.client_id else None
    return templates.TemplateResponse(
        request=request,
        name="template.html",
        context={
            "client": client,
            "csrf_token": session.csrf_token if client else "",
            "status": request.query_params.get("status", ""),
        },
    )


@router.get("/auth/square")
def start_square(request: Request, db: Session = Depends(get_db)):
    token, state = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    try:
        url = SetupService().get_square_authentication_url(state)
    except ValueError as error:
        raise HTTPException(503, "Square onboarding is not configured") from error
    previous = request.cookies.get(COOKIE)
    if previous:
        db.query(SetupSession).filter_by(token_hash=digest(previous)).delete()
    db.query(SetupSession).filter(SetupSession.expires_at <= now()).delete()
    db.add(
        SetupSession(
            token_hash=digest(token),
            state_hash=digest(state),
            csrf_token=secrets.token_urlsafe(32),
            expires_at=now() + timedelta(seconds=settings.SETUP_TTL_SECONDS),
        )
    )
    db.commit()
    response = RedirectResponse(url, status_code=303)
    set_cookie(response, token)
    return response


@router.get("/square-auth/callback")
async def square_callback(request: Request, db: Session = Depends(get_db)):
    session = get_session(request, db)
    state, code = request.query_params.get("state", ""), request.query_params.get("code", "")
    if (
        not state
        or not code
        or not session.state_hash
        or not secrets.compare_digest(session.state_hash, digest(state))
    ):
        raise HTTPException(403, "Invalid OAuth transaction. Connect Square again.")
    token_hash = session.token_hash
    # Atomic compare-and-consume before any provider call; replay/concurrency gets no exchange.
    consumed = (
        db.query(SetupSession)
        .filter(
            SetupSession.token_hash == token_hash,
            SetupSession.state_hash == digest(state),
            SetupSession.expires_at > now(),
        )
        .update({"state_hash": None}, synchronize_session=False)
    )
    db.commit()
    if consumed != 1:
        raise HTTPException(403, "OAuth transaction already used")
    try:
        token = await SetupService().obtain_square_access_token(code)
        async with SquareClient(token["access_token"]) as square:
            merchant = await square.get_merchant_by_id(token["merchant_id"])
        client = ClientService(db).save_square_authorization(token, merchant["business_name"])
        client_id, connected = client.id, bool(client.combo_api_key)
        db.query(SetupSession).filter_by(token_hash=token_hash).delete()
        if not connected:
            # Rotate the browser capability after authentication; never expose client identity as authority.
            browser_token = secrets.token_urlsafe(32)
            db.add(
                SetupSession(
                    token_hash=digest(browser_token),
                    client_id=client_id,
                    csrf_token=secrets.token_urlsafe(32),
                    expires_at=now() + timedelta(seconds=settings.SETUP_TTL_SECONDS),
                )
            )
        db.commit()
    except Exception as error:
        db.rollback()
        logger.warning("Square setup failed: %s", safe_error(error))
        raise HTTPException(502, "Square setup failed. Connect Square again.") from error
    if connected:
        return finished()
    response = RedirectResponse("/", status_code=303)
    set_cookie(response, browser_token)
    return response


@router.post("/combo")
async def connect_combo(request: Request, db: Session = Depends(get_db)):
    # Authenticate before form parsing; fixed configured origin never trusts Host/forwarded headers.
    session = get_session(request, db)
    if not session.client_id or session.state_hash:
        raise HTTPException(403, "Connect Square first")
    if request.headers.get("origin") != settings.APP_URL:
        raise HTTPException(403, "Invalid request origin")
    if (
        request.headers.get("content-type", "").split(";", 1)[0]
        != "application/x-www-form-urlencoded"
    ):
        raise HTTPException(415, "Use the setup form")
    form = await request.form(max_fields=2, max_part_size=16384)
    if (
        set(form.keys()) != {"api_key", "csrf_token"}
        or len(form.getlist("api_key")) != 1
        or len(form.getlist("csrf_token")) != 1
    ):
        raise HTTPException(400, "Invalid setup form")
    csrf, api_key = form["csrf_token"], form["api_key"]
    if not isinstance(csrf, str) or not secrets.compare_digest(session.csrf_token, csrf):
        raise HTTPException(403, "Invalid setup token")
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > 4096:
        raise HTTPException(400, "Invalid Combo key")
    token_hash, client_id = session.token_hash, session.client_id
    client = db.get(Client, client_id)
    if client is None or client.combo_api_key:
        raise HTTPException(409, "Setup no longer available. Connect Square again.")
    try:
        async with ComboClient(api_key.strip()) as combo:
            locations = await combo.get_locations()
        if not locations:
            raise ValueError("No Combo locations")
    except Exception as error:
        logger.warning("Combo validation failed: %s", safe_error(error))
        return RedirectResponse("/?status=invalid-key", status_code=303)
    # Consume and update in one transaction. Concurrent/replayed submissions cannot replace a key.
    consumed = (
        db.query(SetupSession)
        .filter(
            SetupSession.token_hash == token_hash,
            SetupSession.client_id == client_id,
            SetupSession.expires_at > now(),
            SetupSession.csrf_token == csrf,
        )
        .delete(synchronize_session=False)
    )
    updated = (
        db.query(Client)
        .filter(Client.id == client_id, Client.combo_api_key.is_(None))
        .update(
            {"combo_api_key": api_key.strip()},
            synchronize_session=False,
        )
        if consumed == 1
        else 0
    )
    if consumed != 1 or updated != 1:
        db.rollback()
        raise HTTPException(409, "Setup already used or expired")
    db.commit()
    return finished()
