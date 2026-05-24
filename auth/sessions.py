import sqlite3
import uuid
from datetime import datetime, timedelta, timezone


def _conn():
    from data.db import get_db_path
    return sqlite3.connect(get_db_path(), check_same_thread=False)


def create_session(user_id: str, email: str, hours: int = 24) -> str:
    session_id = uuid.uuid4().hex
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO sessions (id, user_id, email, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, email, expires_at),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def get_session_user(session_id: str) -> "dict | None":
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT user_id, email, expires_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    user_id, email, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str)
    if datetime.now(timezone.utc) > expires_at:
        delete_session(session_id)
        return None

    return {"sub": user_id, "email": email}


def delete_session(session_id: str) -> None:
    conn = _conn()
    try:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
