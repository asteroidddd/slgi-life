"""
Park 관련 뷰.

엔드포인트:
- GET /api/adongs/<slug>/parks
  → 행정동에 매핑된 공원 목록 (대시보드 SPEC §4.4 섹션 B "대형 공원" 위젯용)

URL 등록은 apps.service.neighborhoods.urls 에서 한다 (adong-scoped URL 패턴 유지).
DB 스키마 변경 없음 — SELECT 전용.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models import F
from django.db.models.expressions import RawSQL
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# sub-plan 7G-B2: regions.Adong + Gu join ??.
from apps.public_data.regions.models import Adong

from .models import ParkAdong


def _dong_header(adong: Adong) -> dict:
    """공통 adong 식별 dict — apps.service.neighborhoods.views._dong_header 와 동일 포맷.

    응답 dict key set 보존 lock (slug/name/gu). adong.gu는 FK이므로 `.name` 접근.
    """
    return {"slug": adong.slug, "name": adong.name, "gu": adong.gu.name}


@extend_schema(
    tags=["adongs"],
    summary="행정동에 매핑된 공원 목록 (대시보드 §4.4 섹션 B)",
    description=(
        "park_adong 다대다 매핑을 통해 한 행정동에 묶인 공원 전체를 반환한다. "
        "면적(area_m2) 내림차순 정렬 (null은 뒤). 프론트가 큰 공원 N개만 슬라이스해서 표시. "
        "거리(distance_m)는 행정동 중심점(centroid) ↔ 공원 위치(location)의 "
        "ST_DistanceSphere(m). 둘 중 하나라도 좌표가 없으면 null."
    ),
)
class AdongParksView(APIView):
    """
    GET /api/adongs/<slug>/parks

    응답:
      {
        "adong": { "slug": "...", "name": "...", "gu": "..." },
        "count": 12,
        "parks": [
          {
            "id": "P001",
            "name": "남산공원",
            "category": "근린공원",
            "area_m2": 1234567.89,
            "lat": 37.5512,
            "lng": 126.9882,
            "distance_m": 540.3
          },
          ...
        ]
      }

    - parks는 area_m2 내림차순 (null은 뒤).
    - 응답에 모든 매칭 공원 포함 (제한 없음, 프론트가 슬라이스).
    - 매칭이 0건이면 200 + count: 0 + parks: [].
    - distance_m: ST_DistanceSphere(centroid, park.location). 좌표 누락 시 null.
    - 캐시 5분 TTL (키: dong_parks:v1:<slug>).
    """

    def get(self, request: Request, slug: str) -> Response:
        # adong.location? ??? ?? ??? ????.
        try:
            adong = Adong.objects.select_related("gu").get(slug=slug)
        except Adong.DoesNotExist as exc:
            raise NotFound({"detail": "동을 찾을 수 없습니다."}) from exc

        cache_key = f"dong_parks:v1:{slug}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        # park_adong 매핑 → park join.
        # 거리 계산: ST_DistanceSphere 는 4326 그대로 받아서 m 단위 좌표 거리 산출
        # (프로젝트 표준 패턴, score_point.py 참조). geography cast 없이 빠름.
        # park.location 또는 adong.location 중 하나라도 NULL 이면 결과도 NULL.
        # 'park.location' 은 ParkAdong.select_related("park") 시 SQL 별칭이 그대로
        # 테이블명("park")이 된다 (Park.Meta.db_table = "park"). RawSQL은 join 컨텍스트
        # 안에서 평가되므로 join 별칭을 직접 참조한다.
        # adong.location? ??? ?? ??? ????.
        distance_sql = (
            'ST_DistanceSphere('
            '  "park"."location", '
            '  (SELECT location FROM adong WHERE adong.adong_code = %s)'
            ')'
        )
        qs = (
            ParkAdong.objects
            .filter(adong=adong.adong_code)
            .select_related("park")
            .annotate(
                distance_m=RawSQL(distance_sql, (adong.adong_code,)),
            )
            .order_by(F("park__area_m2").desc(nulls_last=True))
            .values(
                "park__id",
                "park__name",
                "park__category",
                "park__area_m2",
                "park__location",  # GeometryField — 좌표 추출용
                "distance_m",
            )
        )

        parks: list[dict] = []
        for row in qs:
            loc = row["park__location"]
            lat = loc.y if loc is not None else None
            lng = loc.x if loc is not None else None
            area = row["park__area_m2"]
            area_f = float(area) if area is not None else None
            dist = row["distance_m"]
            dist_f = float(dist) if dist is not None else None

            parks.append({
                "id": row["park__id"],
                "name": row["park__name"],
                "category": row["park__category"] or "",
                "area_m2": area_f,
                "lat": lat,
                "lng": lng,
                "distance_m": dist_f,
            })

        data = {
            "adong": _dong_header(adong),
            "count": len(parks),
            "parks": parks,
        }

        cache.set(cache_key, data, timeout=300)  # 5분 TTL
        return Response(data, status=status.HTTP_200_OK)
