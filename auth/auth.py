import os
import uuid
import sqlite3
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def _get_db() -> sqlite3.Connection:
    from data.db import get_db_path
    return sqlite3.connect(get_db_path(), check_same_thread=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> "dict | None":
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def register_user(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    if not email or "@" not in email:
        return False, "Invalid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = _get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        if existing:
            return False, "An account with this email already exists."

        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email.lower(), hash_password(password), datetime.now(timezone.utc)),
        )
        conn.commit()
        return True, user_id
    finally:
        conn.close()


def login_user(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, token_or_message)."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        if not row:
            return False, "No account found with this email."
        user_id, password_hash = row
        if not verify_password(password, password_hash):
            return False, "Incorrect password."
        token = create_token(user_id, email.lower())
        return True, token
    finally:
        conn.close()


def create_demo_user_if_missing() -> None:
    """Ensure demo@example.com / demo1234 exists."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@example.com",)
        ).fetchone()
        if not row:
            register_user("demo@example.com", "demo1234")
    finally:
        conn.close()
