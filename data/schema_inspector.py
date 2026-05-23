import pandas as pd
from data.db import get_conn


def get_table_schema(table_name: str, columns_info: list[dict], row_count: int) -> str:
    """Build a human-readable schema string for LLM prompts."""
    lines = [
        f"Table: {table_name}",
        f"Total rows: {row_count}",
        "",
        "Columns:",
    ]
    for col in columns_info:
        samples = ", ".join(f'"{s}"' for s in col["samples"][:3])
        lines.append(f"  - {col['name']} ({col['type']}) — samples: {samples}")
    return "\n".join(lines)
