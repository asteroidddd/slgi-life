# 자취맵 Backend

Django + Django REST Framework + GeoDjango 기반 백엔드입니다. PostgreSQL/PostGIS, Redis, 공공데이터 업데이트 스크립트, 사용자 계정, 지도/히트맵 API, 조건 추천, 동네 정보, 부동산 도우미, AI Agent API를 제공합니다.

## 사전 요구

- Python 3.12 권장
- `uv`
- PostgreSQL/PostGIS 또는 루트 `docker-compose.yml`
- Redis
- GDAL/GEOS/PROJ 시스템 라이브러리

운영 서버에서는 Dockerfile과 Docker Compose가 필요한 시스템 라이브러리와 DB/Redis를 준비합니다.

## 빠른 시작

```bash
cd /home/ubuntu/capston
docker compose up -d db redis
```

```bash
cd /home/ubuntu/capston/backend
cp .env.example .env
uv venv --python 3.12
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e .
python manage.py migrate
python manage.py runserver
```

Docker Compose 전체 실행:

```bash
cd /home/ubuntu/capston
docker compose up -d --build
docker compose ps
```

## 환경 파일

`backend/.env`는 Git에 포함하지 않습니다. 필요한 키 이름은 `backend/.env.example`을 기준으로 맞춥니다.

| 키 | 용도 |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Django settings module |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | 개발/운영 debug 설정 |
| `DJANGO_ALLOWED_HOSTS` | 허용 host |
| `DJANGO_CORS_ALLOWED_ORIGINS` | 프론트엔드 origin |
| `DATABASE_URL` | PostGIS DB 연결 |
| `REDIS_URL` | Redis 연결 |
| `PUBLIC_DATA_API_KEY*` | 공공데이터포털 API 키 |
| `SEOUL_API_KEY` | 서울 열린데이터광장 API 키 |
| `V_WORLD_API_KEY` / `VWORLD_API_KEY` | VWorld API 키 |
| `KOSIS_API_KEY` | KOSIS API 키 |
| `LIFE_INFO_API_KEY` | 생활안전지도 WMS API 키 |
| `KAKAO_REST_API_KEY` | Kakao 로그인 및 주소 fallback REST API 키 |
| `AI_AGENT_*` | AI Agent DB/OpenAI 설정 |

## 앱 구조

| 앱 | 역할 |
|---|---|
| `apps.accounts.user` | 사용자, 로그인, 로그아웃 |
| `apps.accounts.profile` | 내 정보, 주소, 대학 선택지 |
| `apps.accounts.social` | Kakao 로그인 |
| `apps.accounts.favorites` | 담은 동네, 저장된 추천 조건, 호환용 즐겨찾기 API |
| `apps.ai_agent` | 자연어 질의, SQL guard, BYOK API KEY, 대시보드 캐시/원천 테이블 안내 metadata |
| `apps.dashboard.cache` | 동네 정보 화면 캐시, AI 간단 동네 요약용 JSON, 지역 소개, 안전 WMS 프록시 |
| `apps.public_data.*` | 공공데이터 원천 모델과 업데이터 |
| `apps.service.map` | 검색, 서울 마스크, 교통 경로 |
| `apps.service.heatmap` | 행정동/법정동 GeoJSON과 점수 |
| `apps.service.recommend` | 조건 기반 행정동/법정동 추천 |
| `apps.service.amenities` | 지도 영역 내 편의시설 |
| `apps.service.medical` | 의료시설과 진료과목 |
| `apps.service.rent_deal` | 매물 분석, 환산율 |

`AUTH_USER_MODEL`은 `accounts.User`입니다.

## 현재 등록된 API

| API | 앱 | 용도 |
|---|---|---|
| `GET /api/search` | `service.map` | 지역/키워드 검색 |
| `GET /api/map/geojson/seoul-mask` | `service.map` | 서울 외곽 마스크 GeoJSON |
| `GET /api/map/transit-route` | `service.map` | 교통 경로 조회 |
| `GET /api/heatmap/geojson/adongs` | `service.heatmap` | 행정동 GeoJSON |
| `GET /api/heatmap/geojson/ldongs` | `service.heatmap` | 법정동 GeoJSON |
| `GET /api/heatmap/adongs/scores` | `service.heatmap` | 행정동 점수 |
| `GET /api/heatmap/ldongs/scores` | `service.heatmap` | 법정동 점수 |
| `POST /api/recommend/regions` | `service.recommend` | 조건 기반 행정동/법정동 추천 |
| `GET /api/amenities/bbox` | `service.amenities` | 지도 영역 내 편의시설 |
| `GET /api/medical/facilities` | `service.medical` | 의료시설 목록 |
| `GET /api/medical/facilities/<hpid>` | `service.medical` | 의료시설 상세 |
| `GET /api/medical/specialties` | `service.medical` | 의료 진료과목 목록 |
| `GET /api/medical/specialty-groups` | `service.medical` | 의료 진료과목 그룹 목록 |
| `GET /api/dashboard/cache` | `dashboard.cache` | 동네 정보 캐시 |
| `GET /api/dashboard/regions/adongs/lookup` | `dashboard.cache` | 좌표 기준 행정동 lookup |
| `GET /api/dashboard/regions/adongs/<slug>/intro` | `dashboard.cache` | 행정동 소개 |
| `GET /api/dashboard/regions/ldongs/lookup` | `dashboard.cache` | 좌표 기준 법정동 lookup |
| `GET /api/dashboard/regions/ldongs/<slug>/intro` | `dashboard.cache` | 법정동 소개 |
| `GET /api/dashboard/safety/crime-zone` | `dashboard.cache` | 생활안전지도 WMS 프록시 |
| `POST /api/rent-deals/listing-analysis` | `service.rent_deal` | 매물 분석 |
| `GET /api/rent-deals/conversion-rate` | `service.rent_deal` | 보증금-월세 환산율 |
| `POST /api/agent/query` | `ai_agent` | AI Agent 질의 |
| `GET /api/agent/demo/visualization` | `ai_agent` | staff용 AI 시각화 테스트 |
| `DELETE /api/agent/conversation/<conversation_id>` | `ai_agent` | 대화 초기화 |
| `GET/POST /api/agent/api-keys` | `ai_agent` | AI API KEY 상태 조회/저장 |
| `POST /api/agent/api-keys/unlock` | `ai_agent` | 저장된 AI API KEY 잠금 해제 |
| `DELETE /api/agent/api-keys/<provider>` | `ai_agent` | AI API KEY 삭제 |
| `GET/PATCH /api/agent/context-preferences` | `ai_agent` | AI 맥락 공유 설정 |
| `POST /api/auth/login` | `accounts` | 로그인 |
| `POST /api/auth/logout` | `accounts` | 로그아웃 |
| `GET /api/auth/kakao/start` | `accounts.social` | Kakao 로그인 시작 |
| `GET /api/auth/kakao/callback` | `accounts.social` | Kakao 로그인 callback |
| `POST /api/auth/kakao/webhook` | `accounts.social` | Kakao webhook |
| `GET/PATCH /api/users/me` | `accounts` | 내 정보 조회/수정 |
| `GET /api/users/universities` | `accounts` | 대학 선택지 |
| `GET/POST /api/users/me/favorites` | `accounts` | 호환용 즐겨찾기 조회/추가 |
| `DELETE /api/users/me/favorites/<slug>` | `accounts` | 호환용 즐겨찾기 삭제 |
| `GET/PUT /api/users/me/candidate-regions` | `accounts` | 담은 동네 조회/저장 |
| `GET/PUT /api/users/me/recommendation-conditions` | `accounts` | 추천 조건 조회/저장 |

OpenAPI:

```text
/api/schema/
/api/schema/swagger-ui/
/api/schema/redoc/
```

## 동작 확인

```bash
python manage.py check
```

대표 API:

```bash
curl 'http://localhost:8000/api/heatmap/adongs/scores' | python3 -m json.tool
curl 'http://localhost:8000/api/heatmap/ldongs/scores' | python3 -m json.tool
curl 'http://localhost:8000/api/rent-deals/conversion-rate' | python3 -m json.tool
```

Docker Compose:

```bash
cd /home/ubuntu/capston
docker compose exec -T backend python manage.py check
```

## 데이터 업데이트

기본은 dry-run이며 실제 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
python scripts/update/update_dashboard_data.py --target all --write
python scripts/update/update_cache_data.py --target all --write
```

운영 자동 업데이트는 systemd timer `capston-scheduled-update.timer`가 backend 컨테이너 안에서 `scripts/update/scheduled_update.py`를 실행합니다. 상태 JSON은 `backend/scripts/update/.state` 아래에 저장됩니다.

## 주의

- `backend/.env`와 실제 API 키는 커밋하지 않습니다.
- `apps.ai_agent`의 YAML/metadata 파일은 런타임 참조 파일입니다.
- 원천 공공데이터 DB 값은 데이터 업데이트 정책에 맞춰서만 변경합니다.
