from datetime import datetime, timedelta
import hashlib
from db.models import db, User, RefreshToken, DeviceToken

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
REFRESH_TOKEN_DAYS = 30


def find_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def find_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email).first()


def find_by_blockchain_address(address: str) -> User | None:
    return User.query.filter_by(blockchain_address=address).first()


def find_all_by_role(role: str) -> list:
    return User.query.filter_by(role=role).all()


def create(email: str, password: str, role: str, name: str, phone: str,
           blockchain_address: str) -> User:
    user = User(email=email, role=role, blockchain_address=blockchain_address,
                name=name, phone=phone or '')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def record_failed_login(user: User) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
    db.session.commit()


def reset_failed_login(user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()


# ── Refresh tokens ────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(user_id: int) -> str:
    raw = RefreshToken.generate()
    token = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.session.add(token)
    db.session.commit()
    return raw


def find_refresh_token(raw: str) -> RefreshToken | None:
    return RefreshToken.query.filter_by(token_hash=_hash_token(raw), revoked=False).first()


def revoke_refresh_token(raw: str) -> None:
    token = find_refresh_token(raw)
    if token:
        token.revoked = True
        db.session.commit()


def revoke_all_refresh_tokens(user_id: int) -> None:
    RefreshToken.query.filter_by(user_id=user_id, revoked=False).update({'revoked': True})
    db.session.commit()


# ── Device tokens ─────────────────────────────────────────────

def upsert_device_token(user_id: int, token: str, platform: str) -> None:
    existing = DeviceToken.query.filter_by(user_id=user_id, platform=platform).first()
    if existing:
        existing.token = token
        existing.updated_at = datetime.utcnow()
    else:
        db.session.add(DeviceToken(user_id=user_id, token=token, platform=platform))
    db.session.commit()


def get_device_tokens(user_id: int) -> list[str]:
    return [dt.token for dt in DeviceToken.query.filter_by(user_id=user_id).all()]
