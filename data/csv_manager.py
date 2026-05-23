import json
import re
import uuid
from datetime import datetime, timezone

import pandas as pd

from data.db import get_conn


def _sanitize_name(name: str) -> str:
    """Make column/table names SQLite-safe."""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    if name[0].isdigit():
        name = "col_" + name
    return name.lower()


def _make_table_name(user_id: str, file_id: str) -> str:
    return f"u{user_id[:8]}_{file_id[:8]}"


def store_csv(user_id: str, filename: str, df: pd.DataFrame) -> dict:
    """Parse, sanitize, store CSV as SQLite table. Returns file metadata dict."""
    df = df.copy()
    df.columns = [_sanitize_name(c) for c in df.columns]

    file_id = str(uuid.uuid4())
    table_name = _make_table_name(user_id, file_id)

    conn = get_conn()
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)

        columns_info = []
        for col in df.columns:
            sample = df[col].dropna().head(3).astype(str).tolist()
            columns_info.append({
                "name": col,
                "type": str(df[col].dtype),
                "samples": sample,
            })

        conn.execute(
            """INSERT INTO files (id, user_id, filename, table_name, row_count, columns_info, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                file_id,
                user_id,
                filename,
                table_name,
                len(df),
                json.dumps(columns_info),
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": file_id,
        "filename": filename,
        "table_name": table_name,
        "row_count": len(df),
        "columns_info": columns_info,
    }


def list_user_files(user_id: str) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, filename, table_name, row_count, columns_info, created_at FROM files WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r[0],
            "filename": r[1],
            "table_name": r[2],
            "row_count": r[3],
            "columns_info": json.loads(r[4]) if r[4] else [],
            "created_at": r[5],
        }
        for r in rows
    ]


def delete_file(user_id: str, file_id: str) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT table_name FROM files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        if not row:
            return False
        table_name = row[0]
        conn.execute(f"DROP TABLE IF EXISTS [{table_name}]")
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_preview(table_name: str, limit: int = 5) -> pd.DataFrame:
    conn = get_conn(read_only=True)
    try:
        return pd.read_sql_query(f"SELECT * FROM [{table_name}] LIMIT {limit}", conn)
    finally:
        conn.close()


def preload_sample_data(user_id: str, sample_path: str) -> None:
    """Load sample CSV for the demo user if not already present."""
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM files WHERE user_id = ? AND filename = ?",
            (user_id, "ecommerce_sales.csv"),
        ).fetchone()
        if existing:
            return
    finally:
        conn.close()

    df = pd.read_csv(sample_path)
    store_csv(user_id, "ecommerce_sales.csv", df)
