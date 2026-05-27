"""
Adong 시리얼라이저.

- AdongScoreSerializer: SPEC 9 GET /api/adongs/scores 응답 한 항목
  [{slug, name, gu, score, lat, lng, score_rent, score_amenity, score_transit}, ...]
  (raw 점수 3종은 SPEC 14.3 클라 재계산용으로 추가)

- AdongSummarySerializer: SPEC 6.2 GET /api/adongs/:slug/summary 응답
  {slug, name, gu, score, summary, rent_avg, nearest_station,
   amenity_level, safety_level}
  rent_avg/nearest_station/amenity_level/safety_level는
  현재 더미. 실데이터 연동은 10단계(data-pipeline) 이후.
"""

from __future__ import annotations

from datetime import date, timedelta

from rest_framework import serializers

from apps.public_data.rent_deal.models import DEAL_TYPE_TO_HOUSING_TYPE, RentDeal
from apps.public_data.rent_deal.utils import get_monthly_conversion_rate
from apps.public_data.subway.models import NearestSubwayAdong, SubwayStation

from .adong_surface import composite_score as _composite_score
from .detail_dummy import build_dummy_detail  # legacy fallback
from .detail_real import build_real_detail
from .summary import generate_summary


# 5개 더미 동에 한해 가까운 역 하드코딩 (10단계 실 데이터 적재 시 교체).
NEAREST_STATION_FALLBACK: dict[str, dict[str, object]] = {
    "pildong": {"name": "충무로", "line": "4호선", "walking_min": 8},
    "hoegidong": {"name": "회기", "line": "1호선", "walking_min": 5},
    "seogyodong": {"name": "홍대입구", "line": "2호선", "walking_min": 7},
    "yeoksamdong": {"name": "역삼", "line": "2호선", "walking_min": 4},
    "jamsildong": {"name": "잠실", "line": "2/8호선", "walking_min": 6},
}



class AdongScoreSerializer(serializers.Serializer):
    """메인 지도 히트맵용 — 가중합 종합 점수 + 중심점 좌표 + raw 점수 3종.

    7G-B1: ModelSerializer(Adong) → Serializer(Adong wrap). 응답 dict key 보존 lock.
    """

    slug = serializers.CharField()
    code = serializers.CharField()  # 행정동 코드 10자리 — frontend HeatMap GeoJSON adm_cd2 매칭용
    name = serializers.CharField()
    gu = serializers.CharField()
    score = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    # SPEC 14.3: 클라이언트 재계산을 위해 raw 점수 3종 노출.
    score_rent = serializers.FloatField()
    score_amenity = serializers.FloatField()
    score_transit = serializers.FloatField()

    def get_score(self, obj) -> float:
        weights = self.context.get("weights", {"rent": 1 / 3, "amenity": 1 / 3, "transit": 1 / 3})
        return round(
            _composite_score(
                obj,
                w_rent=weights["rent"],
                w_amenity=weights["amenity"],
                w_transit=weights["transit"],
            ),
            2,
        )

    def get_lat(self, obj) -> float:
        # PostGIS PointField: x = lng, y = lat
        return round(obj.centroid.y, 6) if obj.centroid else 0.0

    def get_lng(self, obj) -> float:
        return round(obj.centroid.x, 6) if obj.centroid else 0.0


class AdongSummarySerializer(serializers.Serializer):
    """
    동네 패널(SPEC 6.2)용 요약 응답.

    note: rent_avg / nearest_station / amenity_level / safety_level은
    현재 점수 기반 휴리스틱 또는 slug 매핑으로 더미 값 산출. 10단계
    실데이터 적재 후 raw 데이터 기반으로 교체 예정.

    7G-B1: ModelSerializer(Adong) → Serializer(Adong wrap). 응답 dict key 보존 lock.
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    gu = serializers.CharField()
    score = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    rent_avg = serializers.SerializerMethodField()
    rent_per_m2_avg = serializers.SerializerMethodField()
    nearest_station = serializers.SerializerMethodField()
    nearest_stations = serializers.SerializerMethodField()
    amenity_level = serializers.SerializerMethodField()
    safety_level = serializers.SerializerMethodField()

    # ---- 점수 (가중합) ----
    def get_score(self, obj) -> float:
        weights = self.context.get("weights", {"rent": 1 / 3, "amenity": 1 / 3, "transit": 1 / 3})
        return round(
            _composite_score(
                obj,
                w_rent=weights["rent"],
                w_amenity=weights["amenity"],
                w_transit=weights["transit"],
            ),
            2,
        )

    # ---- 한 줄 요약 (SPEC 11.3 룰베이스) ----
    def get_summary(self, obj) -> str:
        return generate_summary(
            score_rent=obj.score_rent,
            score_amenity=obj.score_amenity,
            score_transit=obj.score_transit,
        )

    # ---- 평균 월세 fallback (만원). score_rent가 높을수록 저렴 ----
    def get_rent_avg(self, obj) -> int:
        return max(0, int(120 - obj.score_rent))

    def get_rent_per_m2_avg(self, obj) -> float | None:
        since = date.today() - timedelta(days=180)
        studio_housing_types = tuple(
            DEAL_TYPE_TO_HOUSING_TYPE[k] for k in ("villa", "dagagu", "danok", "officetel")
        )
        rows = (
            RentDeal.objects.filter(
                adong_id=obj.code,
                contract_date__gte=since,
                housing_type__in=studio_housing_types,
                area_m2__isnull=False,
            )
            .exclude(area_m2=0)
            .values_list("monthly_rent", "deposit", "area_m2")
        )
        values = []
        for monthly_rent, deposit, area_m2 in rows:
            area = float(area_m2 or 0.0)
            if area <= 0:
                continue
            values.append((float(monthly_rent) + float(deposit) * get_monthly_conversion_rate()) / area)
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _nearest_station_rows(self, obj) -> list[dict[str, object]]:
        rows = list(
            NearestSubwayAdong.objects.filter(adong_id=obj.code)
            .order_by("rank")[:3]
        )
        if not rows:
            fallback = NEAREST_STATION_FALLBACK.get(
                obj.slug,
                {"name": "정보 없음", "line": "-", "walking_min": 0},
            )
            return [{"rank": 1, **fallback}]

        names = [row.station_name for row in rows]
        lines_by_name: dict[str, list[str]] = {name: [] for name in names}
        for name, line in SubwayStation.objects.filter(name__in=names).values_list("name", "line"):
            if line not in lines_by_name.setdefault(name, []):
                lines_by_name[name].append(line)

        out = []
        for row in rows:
            lines = lines_by_name.get(row.station_name) or ["-"]
            out.append({
                "rank": row.rank,
                "name": row.station_name,
                "line": " / ".join(lines),
                "walking_min": max(1, int(round(row.distance_m / 70))),
                "walking_distance_m": int(round(row.distance_m)),
            })
        return out

    def get_nearest_station(self, obj) -> dict[str, object]:
        return self._nearest_station_rows(obj)[0]

    def get_nearest_stations(self, obj) -> list[dict[str, object]]:
        return self._nearest_station_rows(obj)

    # ---- amenity_level: score_amenity 구간 ----
    def get_amenity_level(self, obj) -> str:
        score = obj.score_amenity
        if score >= 70:
            return "sufficient"
        if score >= 40:
            return "normal"
        return "lacking"

    # ---- 더미: 안전 지수 (현재 transit 점수 기반 임시 매핑) ----
    # 실데이터(범죄율, CCTV 등)는 5/24 이후 정밀화.
    def get_safety_level(self, obj) -> str:
        score = obj.score_transit
        if score >= 70:
            return "high"
        if score >= 40:
            return "mid"
        return "low"


class AdongCompareItemSerializer(serializers.Serializer):
    """
    동네 비교(SPEC 6.4) 응답의 한 동(adong) 항목.

    `compare_dummy.build_compare_row`가 만든 dict를 그대로 직렬화. 검증/형 변환은
    빌더가 보장하므로 본 시리얼라이저는 필드 정의(스키마)만 책임진다.

    응답 dict는 build_compare_row 출력과 1:1 일치 (snake_case).
    """

    slug = serializers.CharField()
    name = serializers.CharField()
    gu = serializers.CharField()
    score = serializers.FloatField()
    rent_avg = serializers.IntegerField()
    # 환산월세 (만원, 보증금 0.005/월 환산 포함). RentDeal <3건 동은 fallback,
    # 모든 fallback 도 데이터 없으면 null. frontend 는 null-safe 처리 필수.
    rent_converted_avg = serializers.IntegerField(allow_null=True)
    transit_min = serializers.IntegerField()
    amenity_label = serializers.CharField()  # "충분" | "보통" | "부족"
    safety_label = serializers.CharField()  # "높음" | "보통" | "낮음"


class AdongDetailSerializer(serializers.Serializer):
    """
    동네 상세 페이지(SPEC 6.3) 응답 시리얼라이저.

    ModelSerializer가 아니다 — 응답 구조가 6개 섹션의 중첩 dict이라 빌더 함수가
    채운 dict를 그대로 반환하는 것이 명확.

    Phase 4.5 부터 build_real_detail 사용 (RentDeal/Amenity/NearestSubway/BusStop
    실 DB 쿼리). 응답 형식은 build_dummy_detail 과 동일. 예외 발생 시 안전망으로
    build_dummy_detail 로 폴백.
    """

    def to_representation(self, instance) -> dict:
        weights = self.context.get(
            "weights", {"rent": 1 / 3, "amenity": 1 / 3, "transit": 1 / 3}
        )
        try:
            return build_real_detail(instance, weights=weights)
        except Exception:  # pragma: no cover — 운영 안전망
            # 데이터 부재/쿼리 오류 시 dummy 폴백 — 화면이 깨지지 않도록.
            return build_dummy_detail(instance, weights=weights)


# ---------------------------------------------------------------------------
# POST /api/score/point — 임의 지점 커널 점수 (Phase 2a)
# ---------------------------------------------------------------------------
class KernelScoreWeightsSerializer(serializers.Serializer):
    """가중치 dict — `{"rent": 0.3, "amenity": 0.4, "transit": 0.3}`.

    음수 거부. 합이 1이 아니면 View 에서 정규화 (정책: 비율만 의미 있음).
    누락 키는 0.0 (전부 0이면 ValidationError).
    """

    rent = serializers.FloatField(required=False, default=0.0, min_value=0.0)
    amenity = serializers.FloatField(required=False, default=0.0, min_value=0.0)
    transit = serializers.FloatField(required=False, default=0.0, min_value=0.0)


class KernelScoreRequestSerializer(serializers.Serializer):
    """`POST /api/score/point` 요청 본문 검증.

    - lat/lng: 서울 박스 대략 (33~39, 124~131) — 한반도 좌표 sanity. 서울 외도
      허용하되(통학 시간 시뮬), 한국 외 좌표는 거부.
    - weights: 음수 거부. 모두 0이면 거부.
    - school: optional 문자열 (학교명).
    """

    lat = serializers.FloatField(min_value=33.0, max_value=39.0)
    lng = serializers.FloatField(min_value=124.0, max_value=131.0)
    weights = KernelScoreWeightsSerializer()
    school = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_weights(self, weights: dict) -> dict:
        total = (
            weights.get("rent", 0.0)
            + weights.get("amenity", 0.0)
            + weights.get("transit", 0.0)
        )
        if total <= 0:
            raise serializers.ValidationError(
                "rent/amenity/transit 중 하나 이상은 양수여야 합니다."
            )
        # 정규화 (합 1.0 만들기) — Phase 2a SPEC: w_i / sum(w).
        return {k: weights.get(k, 0.0) / total for k in ("rent", "amenity", "transit")}
