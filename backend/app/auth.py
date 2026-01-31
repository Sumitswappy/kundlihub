from __future__ import annotations

import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import jwt
import requests


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(email: str) -> str:
    e = (email or "").strip().lower()
    if not _EMAIL_RE.match(e):
        raise ValueError("Invalid email")
    return e


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_otp(length: int = 6) -> str:
    # Numeric OTP, length 6 by default.
    if length < 4 or length > 10:
        raise ValueError("Invalid OTP length")
    start = 10 ** (length - 1)
    end = (10**length) - 1
    return str(secrets.randbelow(end - start + 1) + start)


def _otp_pepper() -> str:
    # Use a dedicated pepper if present, otherwise fall back to JWT_SECRET.
    pepper = os.getenv("OTP_PEPPER")
    if pepper:
        return pepper
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET is not set (required for OTP hashing)")
    return jwt_secret


def hash_otp(email: str, otp: str) -> str:
    # HMAC(email:otp) -> hex digest
    msg = f"{email}:{otp}".encode("utf-8")
    key = _otp_pepper().encode("utf-8")
    digest = hmac.new(key, msg, sha256).hexdigest()
    return digest


def constant_time_equals(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(str(a), str(b))
    except Exception:
        return False


@dataclass(frozen=True)
class JwtConfig:
    secret: str
    algorithm: str
    access_token_minutes: int


def get_jwt_config() -> JwtConfig:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set. Add it to backend/.env")

    algorithm = os.getenv("JWT_ALG", "HS256")
    minutes = int(os.getenv("JWT_ACCESS_MINUTES", "10080"))  # 7 days
    return JwtConfig(secret=secret, algorithm=algorithm, access_token_minutes=minutes)


def create_access_token(*, user_id: int, email: str) -> str:
    cfg = get_jwt_config()
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=cfg.access_token_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, cfg.secret, algorithm=cfg.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    cfg = get_jwt_config()
    return jwt.decode(token, cfg.secret, algorithms=[cfg.algorithm])


def resend_send_email(*, to_email: str, subject: str, html: str) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set. Add it to backend/.env")
    if not from_email:
        raise RuntimeError("RESEND_FROM_EMAIL is not set. Add it to backend/.env")

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Resend API error: {resp.status_code} {resp.text}")


def send_login_otp_email(*, to_email: str, otp: str, ttl_minutes: int) -> None:
    # Dev convenience: optionally echo OTP to server logs.
    if str(os.getenv("DEV_OTP_ECHO", "")).strip() in {"1", "true", "True", "yes", "YES"}:
        print(f"[DEV_OTP_ECHO] OTP for {to_email}: {otp} (valid {ttl_minutes} min)")

    # Explicitly skip sending emails (useful for local dev without Resend configured).
    if str(os.getenv("DEV_OTP_SKIP_SEND", "")).strip() in {"1", "true", "True", "yes", "YES"}:
        return

    subject = "Your KundliHub login code"
    html = (
        "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>"
        "<h2>Your login code</h2>"
        f"<p style='font-size:18px'>Code: <b>{otp}</b></p>"
        f"<p>This code expires in {ttl_minutes} minutes.</p>"
        "<p>If you didn’t request this, you can ignore this email.</p>"
        "</div>"
    )
    resend_send_email(to_email=to_email, subject=subject, html=html)
