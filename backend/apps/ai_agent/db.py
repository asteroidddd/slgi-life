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

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent.parent


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
from sqlalchemy.exc import SAWarning

_SCHEMA_CONTEXT_CACHE: str | None = None


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


def get_store_codes_text() -> str:
    """config.yaml의 store_codes를 프롬프트용 텍스트로 변환합니다."""
    codes = get_config().get("store_codes", {})
    return "\n".join(f"{name}: {code}" for name, code in codes.items())


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
    """SQLAlchemy가 사용할 수 있도록 read-only DB URL scheme을 정규화한다."""
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
    # LLM이 생성한 SQL은 Django의 쓰기 가능한 DATABASE_URL로 실행하면 안 된다.
    # DB 권한 레벨에서도 막기 위해 AI Agent 전용 read-only 계정을 강제한다.
    database_url = os.environ.get("AI_AGENT_DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "AI_AGENT_DATABASE_URL 환경변수가 필요합니다. "
            "AI Agent는 쓰기 가능한 DATABASE_URL을 사용하지 않습니다."
        )
    return _normalize_database_url(database_url)


def get_db() -> SQLDatabase:
    warnings.filterwarnings("ignore", category=SAWarning)
    return SQLDatabase.from_uri(
        _build_database_url(),
        sample_rows_in_table_info=2,
    )


def get_schema_context() -> str:
    global _SCHEMA_CONTEXT_CACHE
    if _SCHEMA_CONTEXT_CACHE:
        return _SCHEMA_CONTEXT_CACHE

    db = get_db()
    try:
        all_tables = db.get_usable_table_names()
        if "spatial_ref_sys" in all_tables:
            all_tables.remove("spatial_ref_sys")
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
    db = get_db()
    try:
        usable = db.get_usable_table_names()
        valid = [t for t in table_names if t in usable]
        if not valid:
            return get_schema_context()
        return db.get_table_info(valid)
    except Exception:
        return get_schema_context()


def get_llm(model_key: str, temperature: float = 0) -> ChatOpenAI:
    cfg = get_config()
    models = cfg.get("models", {"fast": "gpt-5.4-nano", "smart": "gpt-5.4"})
    sql_cfg = cfg.get("sql", {})

    return ChatOpenAI(
        model=models.get(model_key, models.get("smart", "gpt-5.4")),
        api_key=os.environ.get("AI_AGENT_OPENAI_API_KEY"),
        base_url=os.environ.get("AI_AGENT_OPENAI_BASE_URL"),
        temperature=temperature,
        timeout=sql_cfg.get("timeout", 60),
        max_retries=sql_cfg.get("max_retries", 6),
    )


def get_stage_model(stage: str) -> str:
    """config.yaml의 stage_models에서 단계별 모델 키를 반환합니다."""
    cfg = get_config()
    stage_models = cfg.get("stage_models", {})
    return stage_models.get(stage, cfg.get("models", {}).get("default", "smart"))
