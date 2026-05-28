# 슬기로운 자취생활 Backend

Django + Django REST Framework + GeoDjango 기반 백엔드입니다. PostgreSQL/PostGIS, Redis, 공공데이터 업데이트 스크립트, 사용자 계정, 지도/히트맵 API, AI Agent API를 함께 제공합니다.

## 사전 요구

- Python 3.12 권장
- `uv`
- PostgreSQL/PostGIS 또는 루트 `docker-compose.yml`
- Redis
- GDAL/GEOS/PROJ 시스템 라이브러리

운영 서버에서는 Dockerfile과 Docker Compose가 필요한 시스템 라이브러리와 DB/Redis를 준비합니다.

## 빠른 시작

루트에서 DB와 Redis를 먼저 실행합니다.

```bash
cd /home/ubuntu/capston
docker compose up -d db redis
```

백엔드 개발 환경을 준비합니다.

```bash
cd /home/ubuntu/capston/backend
cp .env.example .env
uv venv --python 3.12
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e .
python manage.py migrate
python manage.py runserver
```

Docker Compose로 백엔드까지 실행하려면 루트에서 실행합니다.

```bash
cd /home/ubuntu/capston
docker compose up -d --build
docker compose ps
```

## 환경 파일

`backend/.env`는 Git에 포함하지 않습니다. 필요한 키 이름은 `backend/.env.example`을 기준으로 맞춥니다.

주요 환경변수:

| 키 | 용도 |
|---|---|
| `DJANGO_SETTINGS_MODULE` | 보통 `config.settings.local` |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | 개발/운영 debug 설정 |
| `DJANGO_ALLOWED_HOSTS` | 허용 host |
| `DJANGO_CORS_ALLOWED_ORIGINS` | 프론트엔드 origin |
| `DATABASE_URL` | PostGIS DB 연결 |
| `REDIS_URL` | Redis 연결 |
| `PUBLIC_DATA_API_KEY*` | 공공데이터포털 API 키 |
| `SEOUL_API_KEY` | 서울 열린데이터광장 API 키 |
| `V_WORLD_API_KEY` | VWorld API 키 |
| `KOSIS_API_KEY` | KOSIS API 키 |
| `AI_AGENT_*` | AI Agent DB/OpenAI 설정 |

## 앱 구조

```text
backend/
├── manage.py
├── pyproject.toml
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   └── urls.py
├── apps/
│   ├── accounts/          # 사용자, 세션 인증, 즐겨찾기
│   ├── ai_agent/          # 자연어 질의, SQL guard, BYOK API 키
│   ├── legacy/            # 과거 neighborhoods 모델 보존
│   ├── public_data/       # 원천 데이터 모델과 업데이터
│   └── service/           # 화면 제공용 서비스 API
├── data/                  # 파일 기반 원천 데이터
└── scripts/               # 업데이트/검증 스크립트
```

`AUTH_USER_MODEL`은 `users.User`입니다. 실제 코드는 `apps.accounts`에 있지만 `AccountsConfig.label = "users"`로 앱 라벨을 유지합니다.

## 현재 등록된 API

프로젝트 URL은 `backend/config/urls.py`에서 `/api/` 하위로 각 앱에 위임합니다.

| API | 앱 | 용도 |
|---|---|---|
| `GET /api/search` | `service.map` | 지역/키워드 검색 |
| `GET /api/map/geojson/seoul-mask` | `service.map` | 서울 외곽 마스크 GeoJSON |
| `GET /api/map/transit-route` | `service.map` | 교통 경로 조회 |
| `GET /api/heatmap/geojson/adongs` | `service.heatmap` | 행정동 GeoJSON |
| `GET /api/heatmap/geojson/ldongs` | `service.heatmap` | 법정동 GeoJSON |
| `GET /api/heatmap/adongs/scores` | `service.heatmap` | 행정동 점수 |
| `GET /api/heatmap/ldongs/scores` | `service.heatmap` | 법정동 점수 |
| `GET /api/transactions/bbox` | `public_data.rent_deal` | 지도 영역 내 전월세 거래 |
| `GET /api/rent-deals/cache` | `service.rent_deal` | 전월세 캐시 |
| `GET /api/rent-deals/match-counts` | `service.rent_deal` | 조건 매칭 개수 |
| `GET /api/rent-deals/conversion-rate` | `service.rent_deal` | 보증금-월세 환산율 |
| `GET /api/rent-deals/<deal_id>` | `service.rent_deal` | 전월세 거래 상세 |
| `GET /api/amenities/bbox` | `service.amenities` | 지도 영역 내 편의시설 |
| `POST /api/agent/query` | `ai_agent` | AI Agent 질의 |
| `DELETE /api/agent/conversation/<conversation_id>` | `ai_agent` | 대화 초기화 |
| `GET/POST /api/agent/api-keys` | `ai_agent` | AI API 키 상태 조회/저장 |
| `POST /api/agent/api-keys/unlock` | `ai_agent` | 저장된 AI API 키 잠금 해제 |
| `DELETE /api/agent/api-keys/<provider>` | `ai_agent` | AI API 키 삭제 |
| `POST /api/auth/register` | `accounts` | 회원가입 |
| `POST /api/auth/login` | `accounts` | 로그인 |
| `POST /api/auth/logout` | `accounts` | 로그아웃 |
| `GET/PATCH /api/users/me` | `accounts` | 내 정보 조회/수정 |
| `GET /api/users/universities` | `accounts` | 학교 선택지 |
| `GET/POST /api/users/me/favorites` | `accounts` | 즐겨찾기 조회/추가 |
| `DELETE /api/users/me/favorites/<slug>` | `accounts` | 즐겨찾기 삭제 |

OpenAPI 문서는 다음 경로에서 확인합니다.

```text
/api/schema/
/api/schema/swagger-ui/
/api/schema/redoc/
```

## 동작 확인

```bash
python manage.py check
```

서버 실행 후 대표 API를 확인합니다.

```bash
curl 'http://localhost:8000/api/heatmap/adongs/scores' | python3 -m json.tool
curl 'http://localhost:8000/api/heatmap/ldongs/scores' | python3 -m json.tool
curl 'http://localhost:8000/api/rent-deals/conversion-rate' | python3 -m json.tool
```

Docker Compose 환경에서는 다음처럼 실행할 수 있습니다.

```bash
cd /home/ubuntu/capston
docker compose exec -T backend python manage.py check
```

## 데이터 업데이트

실제 공공데이터와 서비스 파생 데이터는 업데이트 스크립트로 갱신합니다. 기본 실행은 dry-run이며 실제 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
```

개별 실행:

```bash
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
```

업데이트 상태 JSON은 `backend/apps/public_data/.state` 아래에 저장됩니다.

## GDAL 트러블슈팅

macOS에서 자동 탐지가 실패하면 `.env`에 라이브러리 경로를 명시합니다.

```env
GDAL_LIBRARY_PATH=/opt/homebrew/opt/gdal/lib/libgdal.dylib
GEOS_LIBRARY_PATH=/opt/homebrew/opt/geos/lib/libgeos_c.dylib
```

Linux 컨테이너에서는 `docker-compose.yml`에 설정된 경로를 사용합니다.

```env
GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so
GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so
```

## 주의

- `backend/.env`와 실제 API 키는 커밋하지 않습니다.
- `apps.ai_agent`의 YAML/metadata 파일은 런타임 참조 파일이므로 문서 정리 목적의 수정 대상이 아닙니다.
- 현재 상세/비교/선호 학습 API는 기존 README에 남아 있던 과거 설명과 달리 활성 URL 라우팅에 포함되어 있지 않습니다.
