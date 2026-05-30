# Capston

서울에서 자취를 준비하는 사용자가 지도 위에서 주거비, 생활 편의, 교통 조건을 함께 확인할 수 있도록 돕는 공공데이터 기반 동네 탐색 서비스입니다.

## 현재 서비스 범위

현재 코드는 지도 탐색, 히트맵, 실거래 필터링, 대시보드, 계정 기능, AI 질의 보조를 중심으로 구성되어 있습니다. 과거 상세 페이지와 비교 페이지 코드는 제거되었고, 해당 프론트엔드 경로는 홈 화면으로 리다이렉트됩니다.

핵심 판단 축은 다음 세 가지입니다.

| 축 | 의미 |
|---|---|
| Rent | 주거 비용 부담 |
| Amenity | 생활 편의시설 접근성 |
| Transit | 지하철/버스 접근성 |

## 주요 기능

- 서울 행정동/법정동 지도 기반 탐색
- 행정동/법정동 점수 히트맵
- 지도 영역 내 전월세 실거래 핀 조회
- 조건 기반 전월세 매물 매칭 개수 조회
- 선택 지역 대시보드
- 회원가입, 로그인, 마이페이지, 즐겨찾기
- AI Agent 자연어 질의와 사용자별 API 키 관리

## 주요 화면

| 경로 | 현재 동작 |
|---|---|
| `/` | 메인 지도 탐색 화면 |
| `/dashboard` | 지도/거래/지표 기반 대시보드 |
| `/login` | 로그인 |
| `/register` | 회원가입 |
| `/mypage` | 내 정보와 즐겨찾기 |
| `/design-system` | 개발/디자인 확인용 화면 |
| `/adong/:slug` | 현재 `/`로 리다이렉트 |
| `/adong/:slug/explore` | 현재 `/`로 리다이렉트 |
| `/compare` | 현재 `/`로 리다이렉트 |

## 기술 스택

| 영역 | 내용 |
|---|---|
| Backend | Django, Django REST Framework, GeoDjango |
| Frontend | React 18, Vite, TypeScript |
| Styling | Tailwind CSS v4 |
| Map | Leaflet, react-leaflet, VWorld tile |
| Chart | Recharts |
| Client State | TanStack Query, React Context |
| Database | PostgreSQL/PostGIS |
| Cache | Redis |
| AI Agent | OpenAI API, LangChain |
| Deployment | Docker Compose 기반 단일 서버 운영 |

## 프로젝트 구조

```text
capston/
├── backend/
│   ├── apps/
│   │   ├── accounts/          # 사용자, 인증, 즐겨찾기
│   │   ├── ai_agent/          # 자연어 질의 보조와 BYOK API 키 관리
│   │   ├── public_data/       # 공공데이터 원천 테이블과 업데이터
│   │   └── service/           # 지도, 히트맵, 편의시설, 전월세 서비스 API
│   ├── config/                # Django 설정과 URL 라우팅
│   ├── data/                  # 파일 기반 원천 데이터
│   └── scripts/               # 데이터 업데이트/검증 스크립트
├── frontend/
│   ├── public/                # 정적 파일
│   └── src/
│       ├── components/        # 화면/도메인/UI 컴포넌트
│       ├── contexts/          # 인증/전역 상태
│       ├── hooks/             # API 호출과 화면 상태 hook
│       ├── lib/               # API client, 지도/계산 유틸
│       ├── routes/            # 페이지 라우트
│       ├── styles/            # 전역 스타일
│       └── types/             # 프론트엔드 타입
├── docker-compose.yml
├── initial_setup.sh
├── scripts/
└── DATA_SOURCES.md
```

## 환경 파일

운영 환경 값은 Git에 포함하지 않습니다.

| 파일 | 용도 |
|---|---|
| `backend/.env` | Django, DB, Redis, 외부 API 키, AI Agent 설정 |
| `frontend/.env` | 프론트엔드 API 주소와 지도 키 |
| `secrets/postgres_password.txt` | Docker Compose PostgreSQL 비밀번호 secret |

루트 `.env`는 애플리케이션 런타임에서 사용하지 않습니다. 로컬 작업 자동화나 EC2 접속 보조용으로만 둘 수 있습니다.

Backend에 필요한 외부 API 키 이름은 `backend/.env.example`과 `DATA_SOURCES.md`를 기준으로 맞춥니다.

Frontend 주요 환경변수:

| 키 | 용도 |
|---|---|
| `VITE_API_BASE_URL` | 프론트엔드가 호출할 백엔드 API base URL |
| `VITE_VWORLD_API_KEY` | VWorld 지도 타일 키 |
| `VITE_KAKAO_JS_KEY` | Kakao JavaScript SDK 키 |

Vite는 `VITE_` prefix가 붙은 값만 클라이언트 번들에 노출합니다. 비밀값은 절대 `VITE_` 환경변수에 넣지 않습니다.

## 초기 세팅

서버에 코드와 환경 파일을 배치한 뒤, 루트에서 최초 1회 실행합니다.

```bash
cd /home/ubuntu/capston
./initial_setup.sh
```

이 스크립트는 다음 작업을 순서대로 수행합니다.

1. DB와 Redis 컨테이너 기동
2. Backend 이미지 빌드
3. Django migration 실행
4. AI Agent용 읽기 전용 DB 권한 적용
5. Backend 컨테이너 기동
6. 컨테이너 상태 출력

초기 세팅 전에는 `backend/.env`, `frontend/.env`, `docker-compose.yml`, `secrets/postgres_password.txt`가 현재 서버 환경에 맞는지 확인해야 합니다.

## Backend

Backend는 Django/DRF/GeoDjango 기반입니다. 공공데이터 원천 테이블, 서비스 응답 API, 사용자 기능, AI Agent 기능을 함께 제공합니다.

주요 앱:

| 앱 | 역할 |
|---|---|
| `apps.accounts` | 사용자, 세션 인증, 마이페이지, 즐겨찾기 |
| `apps.ai_agent` | 자연어 질의 기반 보조 기능과 BYOK API 키 관리 |
| `apps.public_data.regions` | 서울 행정구역 코드와 경계 |
| `apps.public_data.rent_deal` | 국토부 전월세 실거래 원천 데이터 |
| `apps.public_data.*` | 인구, 지표, 상권, 교통, 공원, 도서관, 대학 원천 데이터 |
| `apps.service.map` | 검색, 서울 마스크 GeoJSON, 교통 경로 |
| `apps.service.heatmap` | 행정동/법정동 GeoJSON과 점수 API |
| `apps.service.rent_deal` | 전월세 캐시, 조건 매칭, 환산율, 상세 조회 |
| `apps.dashboard` | 대시보드 화면 전용 API와 지역 소개글 |
| `apps.service.amenities` | 지도 영역 내 편의시설 조회 |

로컬 개발 예시:

```bash
cd backend
cp .env.example .env
uv venv --python 3.12
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e .
python manage.py migrate
python manage.py runserver
```

GeoDjango는 GDAL/GEOS/PROJ 시스템 라이브러리가 필요합니다. 운영 컨테이너에서는 Dockerfile 기준으로 설치합니다.

## Frontend

Frontend는 React/Vite/TypeScript 기반 SPA입니다. 지도, 대시보드, 로그인/마이페이지 화면을 제공합니다.

주요 폴더:

| 경로 | 역할 |
|---|---|
| `frontend/src/routes` | `MainMap`, `Dashboard`, 계정 화면, NotFound |
| `frontend/src/components/Map` | 지도, 히트맵, 거래 핀 레이어 |
| `frontend/src/components/Dashboard` | 대시보드 미니맵과 관련 UI |
| `frontend/src/components/Layout` | AI 사이드 패널 등 레이아웃 요소 |
| `frontend/src/components/ui` | 공통 UI 컴포넌트 |
| `frontend/src/hooks` | TanStack Query 기반 API hook |
| `frontend/src/lib` | API client, 지도/점수/계산 유틸 |
| `frontend/src/contexts` | 인증, AI 패널, 페이지 제목 context |
| `frontend/src/styles` | 전역 스타일 |

로컬 개발 예시:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

기본 개발 서버는 `http://localhost:5173`입니다. `vite.config.ts`는 개발 환경에서 `/api` 요청을 `http://localhost:8000`으로 proxy합니다.

자주 쓰는 명령:

```bash
npm run dev
npm run build
npm run typecheck
npm run test
npm run preview
```

## 주요 API

현재 Django URL 라우팅에 등록된 주요 API입니다.

| API | 용도 |
|---|---|
| `GET /api/search` | 지역/키워드 검색 |
| `GET /api/map/geojson/seoul-mask` | 서울 외곽 마스크 GeoJSON |
| `GET /api/map/transit-route` | 교통 경로 조회 |
| `GET /api/heatmap/geojson/adongs` | 행정동 히트맵 GeoJSON |
| `GET /api/heatmap/geojson/ldongs` | 법정동 히트맵 GeoJSON |
| `GET /api/heatmap/adongs/scores` | 행정동 점수 |
| `GET /api/heatmap/ldongs/scores` | 법정동 점수 |
| `GET /api/transactions/bbox` | 지도 영역 내 전월세 거래 |
| `GET /api/rent-deals/cache` | 전월세 캐시 조회/생성 |
| `GET /api/rent-deals/match-counts` | 조건별 전월세 매칭 개수 |
| `GET /api/rent-deals/conversion-rate` | 보증금-월세 환산율 |
| `GET /api/rent-deals/<deal_id>` | 전월세 거래 상세 |
| `GET /api/amenities/bbox` | 지도 영역 내 편의시설 |
| `GET /api/dashboard/regions/adongs/<slug>/intro` | 대시보드 행정동 소개글 |
| `GET /api/dashboard/regions/ldongs/<slug>/intro` | 대시보드 법정동 소개글 |
| `POST /api/agent/query` | AI Agent 질의 |
| `DELETE /api/agent/conversation/<conversation_id>` | AI Agent 대화 초기화 |
| `GET/POST /api/agent/api-keys` | AI API 키 상태 조회/저장 |
| `POST /api/agent/api-keys/unlock` | 저장된 AI API 키 잠금 해제 |
| `DELETE /api/agent/api-keys/<provider>` | AI API 키 삭제 |
| `POST /api/auth/register` | 회원가입 |
| `POST /api/auth/login` | 로그인 |
| `POST /api/auth/logout` | 로그아웃 |
| `GET/PATCH /api/users/me` | 내 정보 조회/수정 |
| `GET /api/users/universities` | 학교 선택지 |
| `GET/POST /api/users/me/favorites` | 즐겨찾기 조회/추가 |
| `DELETE /api/users/me/favorites/<slug>` | 즐겨찾기 삭제 |

## 데이터 업데이트

데이터 업데이트는 backend 스크립트로 수행합니다. 기본 실행은 dry-run이며, 실제 DB 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
```

전체 업데이트 순서:

1. `regions`
2. `metrics`
3. `populations`
4. `rent_deals`
5. `univ`
6. `bus`
7. `subway`
8. `stores`
9. `parks`
10. `library`
11. `amenity`
12. `current`

업데이트 상태 JSON은 `backend/apps/public_data/.state` 아래에 저장됩니다.

## 주요 문서

| 문서 | 용도 |
|---|---|
| `DATA_SOURCES.md` | 원천 데이터, 업데이트 정책, 현재 제공 API |
| `backend/README.md` | 백엔드 개발과 API 요약 |
| `backend/data/DATA_SOURCES.md` | 파일 기반 데이터의 세부 출처 |
| `backend/scripts/README.md` | 업데이트 스크립트 개요 |

## 운영 주의

- `.env` 값, DB 비밀번호, 개인 키는 문서나 Git에 기록하지 않습니다.
- `backend/.env`, `frontend/.env`, `secrets/`, `TEMP/`, `node_modules/`, `dist/`, `*.tsbuildinfo`는 Git에 포함하지 않습니다.
- 마이그레이션 적용 후 데이터 업데이트를 수행합니다.
- 공공데이터 API 호출 제한이 발생하면 해당 실행에서 중단하고 다음 실행에서 이어받습니다.
- 삭제가 필요한 스냅샷성 데이터는 전체 적재 성공 후에만 삭제 반영합니다.
- AI Agent DB 계정은 허용된 조회 테이블만 읽을 수 있도록 권한을 제한합니다.
- Frontend 환경변수 중 `VITE_` prefix 값은 클라이언트에 노출되므로 비밀값을 넣지 않습니다.
