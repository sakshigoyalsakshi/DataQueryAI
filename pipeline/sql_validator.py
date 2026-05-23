import re

BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)
COMMENT_PATTERN = re.compile(r"(--|/\*|\*/)")


def validate_sql(sql: str, allowed_tables: set[str]) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Checks:
    1. No destructive keywords
    2. No SQL comments
    3. Starts with SELECT
    4. References only tables the user owns
    """
    sql_stripped = sql.strip()

    if COMMENT_PATTERN.search(sql_stripped):
        return False, "Query contains SQL comments, which are not allowed."

    if BLOCKED_KEYWORDS.search(sql_stripped):
        match = BLOCKED_KEYWORDS.search(sql_stripped)
        return False, f"Query contains a disallowed keyword: {match.group().upper()}."

    if not sql_stripped.upper().startswith("SELECT"):
        return False, "Only SELECT queries are permitted."

    # Check that the FROM clause only references user-owned tables
    referenced = set(re.findall(r"FROM\s+\[?(\w+)\]?|JOIN\s+\[?(\w+)\]?", sql_stripped, re.IGNORECASE))
    referenced_flat = {t for pair in referenced for t in pair if t}
    unauthorized = referenced_flat - allowed_tables
    if unauthorized:
        return False, f"Query references unauthorized table(s): {', '.join(unauthorized)}."

    return True, ""
