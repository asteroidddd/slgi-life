"""
=============================================================================
데이터베이스 및 설정 관리 모듈 (db.py)
=============================================================================
DB 연결부터 시스템 메타데이터 및 LLM 모델 객체 생성까지 공통적으로 사용되는
핵심 유틸리티 함수들을 제공합니다.

[주요 역할]
  - YAML 설정 로드: config.yaml(모델/파이프라인) 및 table_metadata.yaml(조인/테이블 정보) 캐싱
  - DB 연결: PostgreSQL 연결 및 SQLAlchemy 인스턴스 제공
  - 스키마 관리: DB 스키마 로드 및 캐싱, 프롬프트용 스키마 컨텍스트 반환
  - LLM 인스턴스: 각 단계별 요구사항(빠른 속도 vs 높은 지능)에 맞는 LangChain OpenAI 객체 반환
=============================================================================
"""
import os
import warnings
import yaml
from functools import lru_cache
from pathlib import Path

AI_AGENT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = AI_AGENT_DIR
METADATA_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_AGENT_DIR.parent.parent
SCHEMA_CONTEXT_PATH = METADATA_DIR / "schema_context.yaml"
DOMAIN_DICTIONARY_PATH = METADATA_DIR / "domain_dictionary.yaml"


def _load_env_file(path: Path) -> None:
    """Django 밖에서 단독 실행할 때만 .env를 보조 로드한다."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


# Django 실행 시에는 settings/base.py가 backend/.env를 이미 읽는다.
# 이 로더는 `python agent.py` 같은 단독 실행 경로를 위한 fallback이며 기존 env를 덮지 않는다.
_load_env_file(BACKEND_DIR / ".env")

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SAWarning

_SCHEMA_CONTEXT_CACHE: str | None = None

DOMAIN_DICTIONARY_PROMPT_ROW_LIMITS = {
    "metric": 2000,
    "business_category": 400,
    "ksci_category": 120,
    "gu": 50,
    "adong": 500,
    "ldong": 500,
    "univ": 100,
}
DOMAIN_DICTIONARY_PROMPT_MAX_CHARS = 120_000

AI_SCHEMA_APP_PREFIXES = ("apps.public_data.", "apps.service.", "apps.dashboard.")
AI_SCHEMA_APP_LABELS = {"dashboard"}
AI_SCHEMA_EXCLUDED_TABLES = {
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "django_session",
    "spatial_ref_sys",
    "topology",
    "layer",
    "users",
    "users_groups",
    "users_user_permissions",
    "user_ai_api_key",
    "user_ai_context_preference",
    "user_favorite",
    "rent_deal_geocode_cache",
    "region_amenity_category_cache",
    "region_park_area_cache",
}
AI_SCHEMA_FALLBACK_TABLES = {
    "adjacent_adong",
    "adjacent_gu",
    "adjacent_ldong",
    "adong",
    "adong_population",
    "amenity",
    "amenity_adong",
    "amenity_ldong",
    "bus_congestion",
    "bus_stop",
    "business_category",
    "current_adong",
    "current_gu",
    "current_ldong",
    "current_seoul",
    "dashboard_adong_cache",
    "dashboard_ldong_cache",
    "gu",
    "gu_metric",
    "ksci_category",
    "ldong",
    "ldong_population",
    "library",
    "library_hours",
    "metric",
    "nearest_subway_adong",
    "nearest_subway_ldong",
    "park",
    "park_adong",
    "park_ldong",
    "rent_deal",
    "rent_deal_ldong_adong_map",
    "seoul",
    "seoul_metric",
    "store",
    "subway_congestion",
    "subway_station",
    "univ",
    "univ_adong",
    "univ_ldong",
}


# ── 설정 로더 ─────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_config() -> dict:
    """config.yaml을 로드합니다 (캐시)."""
    path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_table_metadata() -> dict:
    """table_metadata.yaml을 로드합니다 (캐시)."""
    path = os.path.join(os.path.dirname(__file__), "table_metadata.yaml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _load_yaml_file(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    return data if isinstance(data, dict) else {}


def _format_column(column: dict) -> str:
    name = column.get("name", "")
    data_type = column.get("type", "")
    parts = [str(name), str(data_type)]
    if column.get("primary_key"):
        parts.append("PK")
    if not column.get("nullable", True):
        parts.append("NOT NULL")
    if column.get("foreign_key"):
        parts.append(f"FK {column['foreign_key']}")
    if column.get("description"):
        parts.append(f"- {column['description']}")
    return " ".join(part for part in parts if part)


def _format_schema_yaml(data: dict, table_names: list[str] | None = None) -> str:
    tables = data.get("tables") or {}
    if not isinstance(tables, dict):
        return ""

    selected = set(table_names or [])
    lines = ["[schema_context.yaml]"]
    matched = 0
    for table_name in sorted(tables):
        if selected and table_name not in selected:
            continue
        matched += 1
        table = tables.get(table_name) or {}
        lines.append(f"\nTable: {table_name}")
        if table.get("description"):
            lines.append(f"Description: {table['description']}")
        if table.get("app_label") or table.get("model"):
            lines.append(f"Source: {table.get('app_label', '')}.{table.get('model', '')}".rstrip("."))

        columns = table.get("columns") or []
        if columns:
            lines.append("Columns:")
            for column in columns:
                lines.append(f"- {_format_column(column)}")

        primary_key = table.get("primary_key") or []
        if primary_key:
            lines.append(f"Primary key: {', '.join(primary_key)}")

        foreign_keys = table.get("foreign_keys") or []
        if foreign_keys:
            lines.append("Foreign keys:")
            for fk in foreign_keys:
                lines.append(
                    "- "
                    f"{fk.get('column')} -> {fk.get('to_table')}.{fk.get('to_column')}"
                )

        indexes = table.get("indexes") or []
        if indexes:
            lines.append("Indexes:")
            for index in indexes:
                columns_text = ", ".join(index.get("columns") or [])
                unique = " UNIQUE" if index.get("unique") else ""
                lines.append(f"- {index.get('name')}: {columns_text}{unique}")

        geometry_columns = table.get("geometry_columns") or []
        if geometry_columns:
            lines.append(f"Geometry columns: {', '.join(geometry_columns)}")

        if table.get("join_hint"):
            lines.append(f"Join hint: {table['join_hint']}")
        if table.get("note"):
            lines.append(f"Note: {table['note']}")

    return "\n".join(lines).strip() if matched else ""


@lru_cache(maxsize=1)
def get_prebuilt_schema_context() -> str:
    """Return prompt-ready schema text generated from schema_context.yaml."""
    return _format_schema_yaml(_load_yaml_file(SCHEMA_CONTEXT_PATH))


def get_prebuilt_filtered_schema_context(table_names: list[str]) -> str:
    """Return prompt-ready schema text for selected tables from schema_context.yaml."""
    return _format_schema_yaml(_load_yaml_file(SCHEMA_CONTEXT_PATH), table_names=table_names)


@lru_cache(maxsize=1)
def get_domain_dictionary_context() -> str:
    """Return prompt-ready domain values generated from domain_dictionary.yaml."""
    data = _load_yaml_file(DOMAIN_DICTIONARY_PATH)
    domains = data.get("domains") or {}
    if not isinstance(domains, dict):
        return "none"

    lines = ["[domain_dictionary.yaml]"]
    for domain_name in sorted(domains):
        domain = domains.get(domain_name) or {}
        rows = domain.get("rows") or []
        if not rows:
            continue
        lines.append(f"\nDomain: {domain_name}")
        if domain.get("description"):
            lines.append(f"Description: {domain['description']}")
        if domain.get("usage"):
            lines.append(f"Usage: {domain['usage']}")
        limit = DOMAIN_DICTIONARY_PROMPT_ROW_LIMITS.get(domain_name, 200)
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            parts = [f"{key}={value}" for key, value in row.items() if value not in (None, "")]
            if parts:
                lines.append(f"- {'; '.join(parts)}")
            if sum(len(line) + 1 for line in lines) >= DOMAIN_DICTIONARY_PROMPT_MAX_CHARS:
                lines.append("- ... omitted because domain dictionary prompt limit was reached")
                return "\n".join(lines).strip()
        omitted = len(rows) - min(len(rows), limit)
        if omitted > 0:
            lines.append(f"- ... {omitted} rows omitted from prompt; query DB when exact values are needed")

    return "\n".join(lines).strip() if len(lines) > 1 else "none"


def get_store_codes_text() -> str:
    """config.yaml의 store_codes를 프롬프트용 텍스트로 변환합니다."""
    codes = get_config().get("store_codes", {})
    return "\n".join(f"{name}: {code}" for name, code in codes.items())

def get_data_source_labels(table_names: list[str]) -> str:
    """Return user-facing data source labels for selected tables."""
    metadata = get_table_metadata()
    labels = []

    for table in table_names or []:
        table_meta = metadata.get(table) or {}
        for label in table_meta.get("source_labels", []) or []:
            if label and label not in labels:
                labels.append(label)

    return ", ".join(labels) if labels else "서비스 내부 데이터"


def get_join_hints(needed_tables: list[str]) -> str:
    """needed_tables에 해당하는 조인 힌트를 YAML에서 로드해 반환합니다."""
    metadata = get_table_metadata()
    hints = []

    for table in needed_tables:
        if table not in metadata:
            continue
        m = metadata[table]
        lines = [f"[{table}] {m.get('description', '')}"]
        for key, label in [
            ("join_path", "조인"),
            ("sub_join", "서브조인"),
            ("bridge_table", "브릿지"),
            ("filters", "필터"),
            ("to_rent_deal", "월세 경로"),
            ("to_facility", "시설 경로"),
            ("note", "주의"),
        ]:
            if m.get(key):
                lines.append(f"  {label}: {m[key]}")
        hints.append("\n".join(lines))

    return "\n\n".join(hints)


# ── DB 연결 ───────────────────────────────────────────────────────────────────
def _normalize_database_url(database_url: str) -> str:
    """Normalize PostgreSQL URL schemes for SQLAlchemy."""
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgis://"):
        return database_url.replace("postgis://", "postgresql+psycopg://", 1)
    return database_url


def _build_database_url() -> str:
    database_url = os.environ.get("AI_AGENT_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if database_url:
        return _normalize_database_url(database_url)

    required = ["DB_USER", "DB_PASSWORD", "DB_HOST"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    return _normalize_database_url(
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ.get('DB_PORT', 5432)}"
        f"/{os.environ.get('DB_NAME', 'dp_db')}"
    )


@lru_cache(maxsize=1)
def get_ai_model_table_names() -> tuple[str, ...]:
    """Return model-backed tables that AI is allowed to inspect."""
    try:
        from django.apps import apps as django_apps

        if not django_apps.ready:
            raise RuntimeError("Django app registry is not ready.")

        tables: set[str] = set()
        for model in django_apps.get_models():
            app_config = model._meta.app_config
            app_name = app_config.name
            app_label = app_config.label
            if app_name.startswith(AI_SCHEMA_APP_PREFIXES) or app_label in AI_SCHEMA_APP_LABELS:
                tables.add(model._meta.db_table)
        if tables:
            return tuple(sorted(tables - AI_SCHEMA_EXCLUDED_TABLES))
    except Exception:
        pass

    return tuple(sorted(AI_SCHEMA_FALLBACK_TABLES - AI_SCHEMA_EXCLUDED_TABLES))


@lru_cache(maxsize=1)
def get_selectable_table_names() -> tuple[str, ...]:
    """Return public tables that the AI database role can actually SELECT."""
    engine = create_engine(_build_database_url())
    sql = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND has_table_privilege(
                current_user,
                quote_ident(table_schema) || '.' || quote_ident(table_name),
                'SELECT'
              )
        ORDER BY table_name
        """
    )
    with engine.connect() as conn:
        return tuple(row[0] for row in conn.execute(sql).fetchall())


@lru_cache(maxsize=1)
def get_ai_schema_table_names() -> tuple[str, ...]:
    """AI schema allowlist intersected with actual read privileges."""
    allowed = set(get_ai_model_table_names())
    selectable = set(get_selectable_table_names())
    return tuple(sorted((allowed & selectable) - AI_SCHEMA_EXCLUDED_TABLES))


def get_db() -> SQLDatabase:
    warnings.filterwarnings("ignore", category=SAWarning)
    include_tables = list(get_ai_schema_table_names())
    return SQLDatabase.from_uri(
        _build_database_url(),
        include_tables=include_tables or None,
        sample_rows_in_table_info=2,
    )


def get_schema_context() -> str:
    global _SCHEMA_CONTEXT_CACHE
    if _SCHEMA_CONTEXT_CACHE:
        return _SCHEMA_CONTEXT_CACHE

    prebuilt_schema = get_prebuilt_schema_context()
    if prebuilt_schema:
        _SCHEMA_CONTEXT_CACHE = prebuilt_schema
        return _SCHEMA_CONTEXT_CACHE

    db = get_db()
    try:
        all_tables = list(get_ai_schema_table_names())
        if all_tables:
            _SCHEMA_CONTEXT_CACHE = db.get_table_info(table_names=all_tables)
            print(f"\n[시스템 안내] 공공 데이터 테이블 {len(all_tables)}개의 스키마를 성공적으로 로드했습니다.")
        else:
            _SCHEMA_CONTEXT_CACHE = db.get_table_info()
    except Exception as e:
        print(f"\n[시스템 경고] 스키마 로드 중 오류: {e}")
        _SCHEMA_CONTEXT_CACHE = db.get_table_info()

    return _SCHEMA_CONTEXT_CACHE


def get_filtered_schema_context(table_names: list[str]) -> str:
    prebuilt_schema = get_prebuilt_filtered_schema_context(table_names)
    if prebuilt_schema:
        return prebuilt_schema

    db = get_db()
    try:
        usable = set(get_ai_schema_table_names())
        valid = [t for t in table_names if t in usable]
        if not valid:
            return get_schema_context()
        return db.get_table_info(valid)
    except Exception:
        return get_schema_context()


def get_llm(model_key: str, temperature: float = 0, credentials: dict | None = None) -> ChatOpenAI:
    cfg = get_config()
    models = cfg.get("models", {"fast": "gpt-5.4-nano", "smart": "gpt-5.4"})
    sql_cfg = cfg.get("sql", {})
    credentials = credentials or {}
    api_key = (
        credentials.get("api_key")
        or os.environ.get("AI_AGENT_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    provider = credentials.get("provider")
    if provider == "mindlogic":
        base_url = (
            credentials.get("base_url")
            or os.environ.get("AI_AGENT_OPENAI_BASE_URL")
            or "https://factchat-cloud.mindlogic.ai/v1/gateway"
        )
    elif provider == "openai":
        base_url = credentials.get("base_url")
    else:
        base_url = os.environ.get("AI_AGENT_OPENAI_BASE_URL")

    kwargs = {
        "model": models.get(model_key, models.get("smart", "gpt-5.4")),
        "temperature": temperature,
        "timeout": sql_cfg.get("timeout", 60),
        "max_retries": sql_cfg.get("max_retries", 6),
    }
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


def get_stage_model(stage: str) -> str:
    """config.yaml의 stage_models에서 단계별 모델 키를 반환합니다."""
    cfg = get_config()
    stage_models = cfg.get("stage_models", {})
    return stage_models.get(stage, cfg.get("models", {}).get("default", "smart"))



def get_neighborhood_coordinates(names: list[str]) -> list[dict]:
    """Look up lat/lng for recommended neighborhood names from adong and ldong."""
    if not names:
        return []
    try:
        engine = create_engine(_build_database_url())
        sql = text("""
            SELECT name, ST_Y(location) AS lat, ST_X(location) AS lng FROM adong
            WHERE name = ANY(:names) AND location IS NOT NULL
            UNION
            SELECT name, ST_Y(location) AS lat, ST_X(location) AS lng FROM ldong
            WHERE name = ANY(:names) AND location IS NOT NULL
        """)
        with engine.connect() as conn:
            rows = conn.execute(sql, {"names": names}).fetchall()
        seen: set[str] = set()
        result = []
        for row in rows:
            name = row[0]
            if name not in seen:
                seen.add(name)
                result.append({"name": name, "lat": float(row[1]), "lng": float(row[2])})
        return result
    except Exception as e:
        print(f"[coordinate lookup failed] {e}")
        return []
