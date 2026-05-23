import sqlite3

import pandas as pd

from data.db import get_db_path


def execute_query(sql: str) -> "tuple[pd.DataFrame | None, str | None]":
    """
    Run a validated SQL query on the SQLite DB in read-only mode.
    Returns (dataframe, None) on success or (None, error_message) on failure.
    """
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        try:
            df = pd.read_sql_query(sql, conn)
            return df, None
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        return None, f"SQL execution error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"
