"""SLGI step 7G-B1 합성 어댑터 — Adong + CurrentAdong + Gu 조인을 기존 Adong 인터페이스로 노출.

목적
----
sub-plan 7G(Adong removal). `apps.service.neighborhoods.Adong` 의존 제거 작업 단계에서,
8개 핵심 파일(views/serializers/detail_real/detail_dummy/compare_dummy/match/score_point/admin)
이 사용하던 Adong 인스턴스 속성/메서드 인터페이스를 Adong+current_score+Gu 합성으로
대체하기 위한 헬퍼.

?? ?? (?? ?? -> regions.Adong + current_score)
- adong.slug                ↔ adong.slug
- adong.name                ↔ adong.name
- adong.gu                  ↔ adong.gu.name      (한글 구 이름, CharField 호환)
- adong.code                ↔ adong.adong_code   (10자리 행정동 코드)
- adong.id                  ↔ adong.adong_code   (PK. Adong은 adong_code가 PK)
- adong.geom                ↔ adong.boundary
- adong.centroid            ↔ adong.location
- adong.area_km2            ↔ adong.area_m2 / 1_000_000   (annotate)
- adong.score_rent          ↔ adong.current_score.score_rent  (NULL→0, 결정 1A)
- adong.score_amenity       ↔ adong.current_score.score_amenity
- adong.score_transit       ↔ adong.current_score.score_transit
- adong.composite_score(..) ↔ composite_score(adong, ...) helper 함수

사용 패턴
---------
1) queryset 빌더: `build_adong_qs()` — Adong queryset + select_related('gu')
   + Coalesce annotate (score_rent NULL→0). 호출부는 .filter / .only / .get 등을
   기존 Adong queryset 패턴 그대로 chain 한다.

2) 속성 어댑터: `wrap(adong)` — `Adong` 인스턴스를 받아 Adong 인터페이스 호환 객체로
   감싼다. 응답 dict key 보존 lock (frontend 변경 0).

3) composite helper: `composite_score(obj, w_rent, w_amenity, w_transit)` — Adong/wrap
   객체 모두에서 호출 가능. raw 점수 3종을 가중합.

성능
----
- `select_related('gu')` 1쿼리. current_score는 OneToOneField(reverse) — `select_related`
  가능. annotate Coalesce는 SQL 단 한 컬럼.
- legacy Adong qs와 row count 동일(425개 대형 list 시 동일 비용).

응답 dict key 보존
-----------------
- `gu` 응답 필드는 한글 구 이름 (Adong.gu) 그대로 — `adong.gu.name` 사용으로 유지.
- `code` 응답 필드는 10자리 행정동 코드 (Adong.code) — `adong.adong_code` 사용으로 유지.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from django.db.models import ExpressionWrapper, F, FloatField, QuerySet, Value
from django.db.models.functions import Coalesce


# ---------------------------------------------------------------------------
# Queryset builder
# ---------------------------------------------------------------------------
def build_adong_qs() -> "QuerySet":
    """Adong queryset — gu/current_score select_related + area_km2/score_* annotate.

    score_rent는 current_adong.score_rent NULL → 0.0 (결정 1A — capston Adong default=0 정합).

    호출부는 이 queryset에 .filter(...)/.get(slug=...)/.only(...) 등 chain 가능하며,
    wrap()으로 Adong 인터페이스 호환 객체로 감싸 사용한다.
    """
    from apps.public_data.regions.models import Adong  # noqa: WPS433 (지연 import)

    return (
        Adong.objects.select_related("gu", "current_score")
        .annotate(
            area_km2_anno=ExpressionWrapper(
                F("area_m2") / Value(1_000_000.0),
                output_field=FloatField(),
            ),
            score_rent_anno=Coalesce(
                F("current_score__score_rent"),
                Value(0.0),
                output_field=FloatField(),
            ),
            score_amenity_anno=Coalesce(
                F("current_score__score_amenity"),
                Value(0.0),
                output_field=FloatField(),
            ),
            score_transit_anno=Coalesce(
                F("current_score__score_transit"),
                Value(0.0),
                output_field=FloatField(),
            ),
        )
    )


# ---------------------------------------------------------------------------
# composite_score helper (Adong.composite_score 대체)
# ---------------------------------------------------------------------------
def composite_score(obj: Any, w_rent: float, w_amenity: float, w_transit: float) -> float:
    """raw 점수 3종 가중합 — Adong.composite_score 메서드와 동일 식.

    `obj` 는 wrap() 결과 또는 score_rent/score_amenity/score_transit 속성을 가진
    임의 객체.
    """
    return (
        float(obj.score_rent) * w_rent
        + float(obj.score_amenity) * w_amenity
        + float(obj.score_transit) * w_transit
    )


# ---------------------------------------------------------------------------
# wrap: Adong 인스턴스 → Adong 인터페이스 호환 어댑터
# ---------------------------------------------------------------------------
def wrap(adong: Any) -> SimpleNamespace:
    """Adong 인스턴스(build_adong_qs annotate 완료)를 Adong 호환 SimpleNamespace로 변환.

    반환 객체는 다음 속성을 가진다:
      slug, name, gu (한글 string), code (10자리), id (=code),
      geom, centroid, area_km2,
      score_rent, score_amenity, score_transit,
      composite_score(w_rent, w_amenity, w_transit) — 메서드

    annotate가 안 된 raw Adong 인스턴스에도 동작하도록 fallback:
      - score_*_anno 없으면 adong.current_score.score_* 직접 참조 (NULL→0)
      - area_km2_anno 없으면 area_m2 / 1_000_000
    """
    # score_* — annotate 우선, 없으면 reverse relation 직접 조회
    if hasattr(adong, "score_rent_anno"):
        score_rent = float(adong.score_rent_anno or 0.0)
        score_amenity = float(adong.score_amenity_anno or 0.0)
        score_transit = float(adong.score_transit_anno or 0.0)
    else:
        cs = getattr(adong, "current_score", None)
        score_rent = float(cs.score_rent) if (cs and cs.score_rent is not None) else 0.0
        score_amenity = float(cs.score_amenity) if (cs and cs.score_amenity is not None) else 0.0
        score_transit = float(cs.score_transit) if (cs and cs.score_transit is not None) else 0.0

    # area_km2 — annotate 우선, 없으면 area_m2 환산
    if hasattr(adong, "area_km2_anno") and adong.area_km2_anno is not None:
        area_km2 = float(adong.area_km2_anno)
    elif adong.area_m2 is not None:
        area_km2 = float(adong.area_m2) / 1_000_000.0
    else:
        area_km2 = 0.0

    ns = SimpleNamespace(
        # 식별자
        slug=adong.slug,
        name=adong.name,
        gu=adong.gu.name if adong.gu_id else "",  # 한글 구 이름 — Adong.gu(CharField) 호환
        code=adong.adong_code,
        id=adong.adong_code,  # legacy id 호환. PK 의미만 유지.
        # 공간
        geom=adong.boundary,
        centroid=adong.location,
        area_km2=area_km2,
        # 점수 (raw)
        score_rent=score_rent,
        score_amenity=score_amenity,
        score_transit=score_transit,
        # 원본 Adong 보관 (필요시 직접 접근)
        _adong=adong,
    )
    # composite_score 메서드 attach (Adong.composite_score 호환)
    ns.composite_score = lambda w_rent, w_amenity, w_transit, _o=ns: composite_score(
        _o, w_rent, w_amenity, w_transit
    )
    return ns
