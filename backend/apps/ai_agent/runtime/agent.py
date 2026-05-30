"""
=============================================================================
슬기로운 자취생활 - AI Agent 메인 파이프라인 (agent.py)
=============================================================================
이 모듈은 사용자 질문을 받아 DB 조회를 통해 답변을 생성하는 전체 과정을 조율합니다.

[핵심 파이프라인]
  1. 질문 분류 (Classification): 질문의 의도를 파악하고 필요한 테이블과 조인 힌트를 추출합니다.
  2. SQL 실행 (Text-to-SQL): LLM을 활용해 쿼리를 생성하고, DB에서 실행 및 품질을 검증합니다.
  3. 응답 생성 (Selection/Info): 조회된 데이터를 기반으로 사용자 맞춤형 자연어 답변과 시각화 데이터를 구성합니다.

[실행 방법]
  - 패키지 설치: pip install langchain langchain-openai langchain-community sqlalchemy psycopg2-binary python-dotenv pyyaml
  - 터미널 환경: python agent.py "질문 내용"
  - 대화형 모드: python agent.py 실행 후 프롬프트에 질문 입력
=============================================================================
"""

import json
import time
import argparse
from langchain_core.messages import SystemMessage, HumanMessage

# Use relative imports inside the Django apps.ai_agent package.
from ..metadata.context import (
    get_config,
    get_db,
    get_domain_dictionary_context,
    get_llm,
    get_schema_context,
    get_stage_model,
    get_store_codes_text,
)
from .schemas import ClassificationOutput, SelectionOutput, InfoOutput
from .sql_runner import run_text_to_sql
from ..helpers.sql_guard import validate_read_only_sql
from .prompts import CLASSIFICATION_PROMPT, SELECTION_PROMPT, INFO_ANSWER_PROMPT

def _format_memory_item(item: dict) -> str:
    label = str(item.get("label", "")).strip()
    kind = str(item.get("kind", "")).strip()
    source = str(item.get("source", "")).strip()
    data = item.get("data") or {}
    columns = data.get("columns") or {}

    details = []
    if source:
        details.append(f"출처={source}")
    if data.get("value") is not None:
        details.append(f"값={data.get('value')}")
    if data.get("lat") is not None and data.get("lng") is not None:
        details.append(f"위치좌표=lat {data.get('lat')}, lng {data.get('lng')}")
    if columns:
        col_text = ", ".join(
            f"{key}: {value}" for key, value in list(columns.items())[:6]
        )
        details.append(col_text)

    prefix = f"[{kind}] " if kind else ""
    suffix = f" ({' | '.join(details)})" if details else ""
    return f"{prefix}{label}{suffix}"


def _latest_memory_context(history: list) -> str:
    for entry in reversed(history):
        memory_items = entry.get("memory_items") or []
        if memory_items:
            lines = [
                _format_memory_item(item)
                for item in memory_items[:10]
                if item.get("label")
            ]
            if lines:
                return "\n".join(f"- {line}" for line in lines)
    return ""


def _format_history(history: list) -> str:
    """대화 히스토리를 프롬프트에 삽입할 텍스트로 변환합니다."""
    if not history:
        return "없음"
    lines = []
    for i, entry in enumerate(history[-5:], 1):
        lines.append(f"[{i}번째 대화]")
        lines.append(f"사용자: {entry['question']}")

        if entry.get("neighborhoods"):
            hoods = ", ".join(
                f"{n.get('gu_name', '')} {n.get('ldong_name', '')}(법정동)"
                for n in entry["neighborhoods"]
            )
            lines.append(f"추천된 동네(법정동 이름): {hoods}")

        if entry.get("memory_items"):
            lines.append("이전 응답의 주요 결과:")
            for item in entry["memory_items"][:10]:
                if item.get("label"):
                    lines.append(f"- {_format_memory_item(item)}")

        lines.append(f"AI: {entry['answer'][:300]}")
        lines.append("")

    return "\n".join(lines)


def _enrich_question(question: str, history: list) -> str:
    """이전 결과를 질문 앞에 붙여 SQL 생성 단계에서도 맥락을 이해하게 합니다."""
    if not history:
        return question

    context_blocks = []

    for entry in reversed(history):
        if entry.get("neighborhoods"):
            hoods = ", ".join(
                f"{n.get('gu_name', '')} {n.get('ldong_name', '')}"
                for n in entry["neighborhoods"]
            )
            context_blocks.append(
                f"[이전 추천 동네(법정동 이름): {hoods}]\n"
                "※ 이 동네 이름은 법정동(ldong)입니다. 시설 조회 시 amenity_ldong → ldong.name 경로를 사용하세요."
            )
            break

    memory_context = _latest_memory_context(history)
    if memory_context:
        context_blocks.append(
            "[이전 응답 주요 결과]\n"
            f"{memory_context}\n"
            "※ 사용자의 '거기', '그곳', '첫 번째', '두 번째', '방금 말한 곳', '아까 말한 것'은 위 결과를 가리킬 수 있습니다."
        )

    if not context_blocks:
        return question

    return "\n".join(context_blocks) + f"\n{question}"

def _format_user_context(user_context: dict | None) -> str:
    if not user_context:
        return "없음"

    lines = []
    school = user_context.get("school")
    if school:
        lines.append(f"학교: {school}")

    home_location = user_context.get("home_location") or {}
    lat = home_location.get("lat")
    lng = home_location.get("lng")
    if lat is not None and lng is not None:
        lines.append(f"집 위치 좌표: lat={lat}, lng={lng}")
        lines.append("주소 원문은 제공되지 않았습니다. 답변에 좌표를 그대로 노출하지 마세요.")

    return "\n".join(lines) if lines else "없음"


def run_agent(
    question: str,
    history: list | None = None,
    llm_credentials: dict | None = None,
    user_context: dict | None = None,
) -> dict:
    """
    파이프라인:
      1단계: 질문 분류  — route / query_type / needed_tables / join_hint
      2단계: SQL 실행   — Text-to-SQL + YAML 힌트 + 재시도
      3단계: 응답 생성  — query_type별 분기 (config.yaml의 query_types 기반)

    Args:
        question: 사용자 질문
        history:  이전 대화 목록. 각 항목은 {"question", "answer", "neighborhoods"} 딕셔너리
    """
    history = history or []
    start = time.time()
    cfg = get_config()
    pipeline_cfg = cfg.get("pipeline", {})
    max_neighborhoods = pipeline_cfg.get("max_neighborhoods", 2)

    print(f"\n{'='*60}")
    print(f"질문: {question}")
    print(f"{'='*60}")

    schema_context = get_schema_context()
    conversation_history = _format_history(history)
    enriched_question = _enrich_question(question, history)
    formatted_user_context = _format_user_context(user_context)

    # ── 1단계: 질문 분류 ──────────────────────────────────────────────────────
    print("\n[1단계] 질문 분류 중...")
    llm_cls = get_llm(get_stage_model("classification"), credentials=llm_credentials)
    classification = llm_cls.with_structured_output(
        ClassificationOutput, method="function_calling"
    ).invoke([
        SystemMessage(content=CLASSIFICATION_PROMPT.format(
            schema_context=schema_context,
            store_codes=get_store_codes_text(),
            domain_dictionary=get_domain_dictionary_context(),
            conversation_history=conversation_history,
            user_context=formatted_user_context,
        )),
        HumanMessage(content=question),
    ])

    print(f"  route:         {classification.route}")
    print(f"  query_type:    {classification.query_type}")
    print(f"  needed_tables: {classification.needed_tables}")
    print(f"  join_hint:     {classification.join_hint}")

    if classification.route in {"direct", "blocked"}:
        if classification.route == "blocked":
            answer = "저는 서울 자취/동네 추천 서비스예요. 동네 추천, 월세, 주변 시설 등에 대해 물어봐 주세요! 😊"
        else:
            answer = classification.message

        return {
            "answer": answer,
            "neighborhoods": [],
            "visualizations": [],
            "route": classification.route,
            "query_type": classification.query_type,
            "sql": None,
            "elapsed_sec": round(time.time() - start, 2),
        }

    # ── 2단계: SQL 실행 ───────────────────────────────────────────────────────
    print("\n[2단계] SQL 생성 및 실행 중...")
    sql_result = run_text_to_sql(
        question=enriched_question,
        needed_tables=classification.needed_tables,
        join_hint=classification.join_hint,
        sql_plans=[p.model_dump() for p in classification.sql_plans],
        llm_credentials=llm_credentials,
        user_context=formatted_user_context,
    )

    # ── 3단계: query_type별 분기 ──────────────────────────────────────────────
    query_types_cfg = cfg.get("query_types", {})
    qt_cfg = query_types_cfg.get(classification.query_type, {})
    steps = qt_cfg.get("steps", [])

    if "info_answer" in steps:
        print("\n[3단계] 정보 조회 답변 생성 중...")
        llm_info = get_llm(get_stage_model("info_answer"), credentials=llm_credentials)

        info_result = llm_info.with_structured_output(
            InfoOutput, method="function_calling"
        ).invoke([
            SystemMessage(content=INFO_ANSWER_PROMPT),
            HumanMessage(content=f"질문: {enriched_question}\nSQL 결과: {sql_result['result'] or '조회 결과 없음'}"),
        ])

        elapsed = round(time.time() - start, 2)
        print(f"\n[최종 답변]\n{info_result.answer}")
        print(f"\n총 소요시간: {elapsed}초 | SQL 시도: {sql_result.get('attempts', 0)}회")

        return {
            "answer": info_result.answer,
            "neighborhoods": [],
            "visualizations": [
                {
                    "type": info_result.visualization_type,
                    "title": info_result.visualization_title,
                    "unit": info_result.visualization_unit,
                    "data": [d.model_dump() for d in info_result.visualization_data],
                }
            ] if info_result.visualization_type != "none" else [],
            "route": "db",
            "query_type": classification.query_type,
            "sql": sql_result.get("sql"),
            "sql_attempts": sql_result.get("attempts", 0),
            "elapsed_sec": elapsed,
        }

    if "selection" in steps:
        print("\n[3단계] 동네 선정 중...")
        llm_sel = get_llm(get_stage_model("selection"), credentials=llm_credentials)

        selection = llm_sel.with_structured_output(
            SelectionOutput, method="function_calling"
        ).invoke([
            SystemMessage(content=SELECTION_PROMPT.format(
                question=enriched_question,
                sql_result=sql_result["result"] or "조회 결과 없음",
                max_neighborhoods=max_neighborhoods,
            )),
            HumanMessage(content=enriched_question),
        ])

        # 보강 쿼리 실행
        if selection.additional_sql:
            print(f"\n[보강 쿼리]\n{selection.additional_sql}")
            try:
                additional_sql = validate_read_only_sql(selection.additional_sql)
                db = get_db()
                extra = db.run(additional_sql)
                print(f"[보강 결과] {extra[:200] if extra else '비어있음'}")

                if extra and extra.strip() not in ("", "[]"):
                    enriched = (
                        f"{sql_result['result']}"
                        f"\n\n[보강 데이터 — 비교 기준]\n"
                        f"SQL: {additional_sql}\n"
                        f"결과: {extra}\n"
                        f"※ 한줄평, data_summary, visualization_data에 반드시 반영하세요"
                    )
                    selection = llm_sel.with_structured_output(
                        SelectionOutput, method="function_calling"
                    ).invoke([
                        SystemMessage(content=SELECTION_PROMPT.format(
                            question=enriched_question,
                            sql_result=enriched,
                            max_neighborhoods=max_neighborhoods,
                        )),
                        HumanMessage(content=enriched_question),
                    ])
            except Exception as e:
                print(f"[보강 쿼리 실패] {e}")

        elapsed = round(time.time() - start, 2)
        print(f"\n[최종 답변]\n{selection.answer}")
        print(f"\n총 소요시간: {elapsed}초 | SQL 시도: {sql_result.get('attempts', 0)}회")

        return {
            "answer": selection.answer,
            "neighborhoods": [n.model_dump() for n in selection.neighborhoods],
            "visualizations": [
                {
                    "type": v.type,
                    "title": v.title,
                    "unit": v.unit,
                    "data": [d.model_dump() for d in v.data],
                }
                for v in selection.visualizations
            ],
            "route": "db",
            "query_type": classification.query_type,
            "sql": sql_result.get("sql"),
            "sql_attempts": sql_result.get("attempts", 0),
            "elapsed_sec": elapsed,
        }

    # steps가 비어있는 경우 (direct/blocked가 아닌데 query_type 매핑 없는 경우)
    elapsed = round(time.time() - start, 2)
    return {
        "answer": "처리할 수 없는 요청입니다.",
        "neighborhoods": [],
        "visualizations": [],
        "route": classification.route,
        "query_type": classification.query_type,
        "sql": None,
        "elapsed_sec": elapsed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="슬기로운 자취생활 AI Agent")
    parser.add_argument("question", nargs="?", default=None)
    args = parser.parse_args()

    if args.question:
        result = run_agent(args.question)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("슬기로운 자취생활 AI Agent")
        print("종료: Ctrl+C | 히스토리 초기화: /clear\n")
        history = []
        while True:
            try:
                q = input("질문: ").strip()
                if not q:
                    continue
                if q == "/clear":
                    history = []
                    print("대화 기록을 초기화했습니다.\n")
                    continue
                result = run_agent(q, history=history)
                history.append({
                    "question": q,
                    "answer": result.get("answer", ""),
                    "neighborhoods": result.get("neighborhoods", []),
                })
                history = history[-10:]
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except KeyboardInterrupt:
                print("\n종료합니다.")
                break
