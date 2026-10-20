from __future__ import annotations
import base64, hashlib, hmac, os, secrets
from typing import Iterable
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Worker

ROLE_ADMIN = "admin"
ROLE_WORKER = "worker"
ROLE_READER = "reader"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    rounds = 240_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algo, rounds, salt_b64, digest_b64 = encoded.split("$", 3)
        if algo != "pbkdf2_sha256": return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def get_current_user(request: Request, db: Session) -> Worker | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    user = db.get(Worker, int(uid))
    if not user or not user.active:
        request.session.clear()
        return None
    return user


def require_user(request: Request, db: Session, roles: Iterable[str] | None = None) -> Worker:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(303, headers={"Location": f"/login?next={request.url.path}"})
    if roles and user.role not in set(roles):
        raise HTTPException(403, "K této části nemáte oprávnění.")
    return user


def ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def check_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get("csrf")
    if not expected or not token or not hmac.compare_digest(expected, token):
        raise HTTPException(400, "Neplatný ochranný token formuláře. Obnovte stránku a zkuste to znovu.")
