import re


class UnsafeSQL(ValueError):
    """Raised when an LLM-generated SQL query is not safe to execute."""


BANNED_KEYWORDS = {
    "alter",
    "call",
    "comment",
    "copy",
    "create",
    "delete",
    "do",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "refresh",
    "reset",
    "revoke",
    "set",
    "truncate",
    "update",
    "vacuum",
}
GEOMETRY_COLUMNS = {"boundary", "geom", "geometry", "location"}
LARGE_TABLES = {"bus_congestion", "rent_deal"}
MAX_LIMIT = 100


def validate_read_only_sql(sql: str) -> str:
    """
    Return a normalized SQL string only if it is safe enough to execute.

    The database role is read-only, but this guard keeps obvious destructive,
    multi-statement, or unbounded LLM output from reaching PostgreSQL at all.
    """
    cleaned = _strip_sql(sql)
    lowered = cleaned.lower()

    if not cleaned:
        raise UnsafeSQL("SQL이 비어 있습니다.")
    if "--" in lowered or "/*" in lowered or "*/" in lowered:
        raise UnsafeSQL("SQL 주석은 허용하지 않습니다.")
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
        lowered = cleaned.lower()
    if ";" in cleaned:
        raise UnsafeSQL("다중 SQL 문장은 허용하지 않습니다.")
    if not re.match(r"^\s*(select|with)\b", lowered):
        raise UnsafeSQL("SELECT 또는 WITH SELECT 쿼리만 허용합니다.")

    banned = sorted(word for word in BANNED_KEYWORDS if re.search(rf"\b{word}\b", lowered))
    if banned:
        raise UnsafeSQL(f"허용하지 않는 SQL 키워드가 포함되어 있습니다: {', '.join(banned)}")

    select_clause = _first_select_clause(lowered)
    if _selects_all_columns(select_clause):
        raise UnsafeSQL("SELECT * 또는 table.* 조회는 허용하지 않습니다.")
    selected_geometry = sorted(
        col for col in GEOMETRY_COLUMNS if re.search(rf"(\b|\.){col}\b", select_clause)
    )
    if selected_geometry:
        raise UnsafeSQL(
            "공간 컬럼은 응답에 포함하지 않습니다: " + ", ".join(selected_geometry)
        )

    _validate_limits(lowered)
    _validate_large_tables(lowered, select_clause)
    return cleaned


def _strip_sql(sql: str) -> str:
    stripped = sql.strip()
    if stripped.startswith("```sql"):
        stripped = stripped.removeprefix("```sql").strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped


def _first_select_clause(lowered_sql: str) -> str:
    select_pos = lowered_sql.find("select")
    if select_pos < 0:
        return ""
    from_match = re.search(r"\bfrom\b", lowered_sql[select_pos:])
    if not from_match:
        return lowered_sql[select_pos:]
    return lowered_sql[select_pos : select_pos + from_match.start()]


def _selects_all_columns(select_clause: str) -> bool:
    return bool(
        re.search(r"\bselect\s+\*", select_clause)
        or re.search(r",\s*\*", select_clause)
        or re.search(r"\b[a-z_][a-z0-9_]*\.\*", select_clause)
    )


def _validate_limits(lowered_sql: str) -> None:
    limit_matches = list(re.finditer(r"\blimit\s+(\d+)\b", lowered_sql))
    for match in limit_matches:
        if int(match.group(1)) > MAX_LIMIT:
            raise UnsafeSQL(f"LIMIT은 {MAX_LIMIT} 이하만 허용합니다.")
    if re.search(r"\blimit\b", lowered_sql) and not limit_matches:
        raise UnsafeSQL("LIMIT은 숫자 상수로 지정해야 합니다.")


def _validate_large_tables(lowered_sql: str, select_clause: str) -> None:
    for table in LARGE_TABLES:
        if not re.search(rf"\b{table}\b", lowered_sql):
            continue
        if not re.search(r"\bwhere\b", lowered_sql):
            raise UnsafeSQL(f"{table} 조회에는 WHERE 조건이 필요합니다.")
        has_limit = bool(re.search(r"\blimit\s+\d+\b", lowered_sql))
        has_group_by = bool(re.search(r"\bgroup\s+by\b", lowered_sql))
        is_single_aggregate = bool(
            re.search(r"\b(avg|count|sum|min|max|percentile_cont)\s*\(", select_clause)
        )
        if not has_limit and (has_group_by or not is_single_aggregate):
            raise UnsafeSQL(f"{table}의 목록/그룹 조회에는 LIMIT이 필요합니다.")
