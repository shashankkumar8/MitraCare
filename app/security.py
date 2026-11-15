import hashlib, hmac, secrets, os
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from .models import Session as LoginSession, Member

COOKIE = "mitracare_session"

def hash_secret(value: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return f"{salt}${digest}"

def verify_secret(value: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
        actual = hash_secret(value, salt).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError): return False

def token_digest(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()

def create_session(db: Session, member: Member) -> str:
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(member_id=member.id, token_hash=token_digest(token), expires_at=datetime.now(timezone.utc)+timedelta(hours=12)))
    db.commit()
    return token

def current_member(request: Request, db: Session) -> tuple[Member, object]:
    token = request.cookies.get(COOKIE)
    if not token: raise HTTPException(401, "Please sign in to continue.")
    row = db.query(LoginSession).filter_by(token_hash=token_digest(token)).first()
    if not row or (row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at.astimezone(timezone.utc)) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Your session expired. Please sign in again.")
    member = db.get(Member, row.member_id)
    if not member or not member.active: raise HTTPException(401, "This care-circle account is inactive.")
    return member, row

def require_write(member: Member):
    if member.role not in ("patient", "caregiver"):
        raise HTTPException(403, "Family access is view-only. Ask the patient to grant caregiver access.")

def pin_valid(pin: str):
    if not pin.isdigit() or not 6 <= len(pin) <= 8:
        raise HTTPException(422, "PIN must be 6–8 digits.")
