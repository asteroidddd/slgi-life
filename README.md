# 자취맵

자취맵은 서울에서 자취를 준비하는 사용자가 조건 추천, 지도 탐색, 동네 정보, 부동산 도우미, AI 질의를 한 흐름에서 사용할 수 있도록 만든 공공데이터 기반 동네 탐색 서비스입니다.

## 서비스 흐름

| 단계 | 화면 | 역할 |
|---|---|---|
| 시작 | `/select` | 조건 추천 또는 지도 탐색 중 하나를 선택 |
| 조건 추천 | `/recommend/conditions` | 예산, 통학, 선호 시설, 우선순위를 입력 |
| 추천 결과 | `/recommend/results` | 조건에 맞는 행정동/법정동 후보를 확인하고 담기 또는 자세히 보기 |
| 지도 탐색 | `/map` | 시설, 의료, 점수 히트맵을 보며 동네 선택 |
| 동네 정보 | `/dashboard/:regionType/:slug` | 선택한 행정동/법정동의 주거비, 교통, 생활 인프라, 안전 정보 확인 |
| 부동산 도우미 | `/real-estate` | 체크리스트, 매물 분석, 외부 링크 제공 |
| AI | 우측 사이드 패널 | 현재 화면을 유지한 채 AI 채팅 열기 |

`/ai-chat`은 별도 페이지가 아니라 `/select?ai=1`로 이동해 우측 AI 패널을 여는 호환 경로입니다.

## 주요 기능

- 조건 기반 행정동/법정동 추천
- 지도 기반 시설/의료/히트맵 탐색
- 선택 위치 또는 동네에서 동네 정보 화면으로 이동
- 담은 동네 저장, 삭제, 지도 보기, 자세히 보기
- 회원별 담은 동네와 추천 조건 저장
- 대시보드에서 동네 기준 실제 매물 보기 외부 링크 제공
- 동네 정보 화면의 주거비, 교통, 생활 인프라, 안전 지표
- 부동산 도우미의 체크리스트, 매물 분석, 외부 링크
- 사용자 API KEY 기반 AI 질의. 동네 간단 요약은 대시보드 캐시를 우선 활용하고, 상세 근거는 공공데이터 원천 테이블을 조회
- 이용약관, 개인정보처리방침, 데이터출처 페이지

## 판단 지표

| 지표 | 의미 |
|---|---|
| 부동산 | 최근 전월세 실거래 기반 주거비 부담 |
| 교통 | 지하철, 버스, 대학 접근성. 조건 추천 통학 시간은 카카오맵 길찾기 결과를 활용 |
| 편의시설 | 생활, 운동, 의료, 공부 시설 접근성 |
| 안전 | 자치구 안전 원자료를 동 단위 화면에 맞게 표시한 지표 |

## 기술 스택

| 영역 | 내용 |
|---|---|
| Backend | Django, Django REST Framework, GeoDjango |
| Frontend | React 18, Vite, TypeScript |
| Styling | Tailwind CSS v4 |
| Map | Leaflet, react-leaflet, VWorld |
| Chart | Recharts |
| Client State | TanStack Query, React Context |
| Database | PostgreSQL/PostGIS |
| Cache | Redis |
| AI | OpenAI API, LangChain |
| Deployment | Docker Compose |

## 프로젝트 구조

```text
capston/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # 사용자, 프로필, 소셜 로그인, 담은 동네, 추천 조건
│   │   ├── ai_agent/       # AI 질의, BYOK API KEY, SQL guard
│   │   ├── caches/         # 전월세 지오코딩 등 운영 보조 캐시
│   │   ├── dashboard/      # 동네 정보 화면용 캐시/API
│   │   ├── public_data/    # 공공데이터 원천 모델과 업데이터
│   │   └── service/        # 지도, 히트맵, 추천, 편의시설, 의료, 부동산 도우미 API
│   ├── config/             # Django 설정과 URL 라우팅
│   ├── data/               # 파일 기반 원천 데이터
│   └── scripts/            # 업데이트/검증 스크립트
├── frontend/
│   ├── public/
│   └── src/
│       ├── features/       # 도메인별 화면, 컴포넌트, hook, API 타입
│       ├── styles/         # 전역 스타일과 디자인 토큰
│       ├── App.tsx         # SPA 라우팅
│       └── main.tsx
├── scripts/
├── docker-compose.yml
└── DATA_SOURCES.csv
```

## 프론트엔드 라우트

| 경로 | 역할 |
|---|---|
| `/` | `/select`로 이동 |
| `/select` | 탐색 방식 선택 |
| `/recommend/conditions` | 조건 입력 |
| `/recommend/results` | 추천 결과 |
| `/map` | 지도 탐색 |
| `/dashboard/:regionType` | 행정동/법정동 검색형 동네 정보 |
| `/dashboard/:regionType/:slug` | 특정 행정동/법정동 동네 정보 |
| `/real-estate` | 부동산 도우미 |
| `/ai-chat` | `/select?ai=1`로 이동 후 AI 패널 열기 |
| `/legal/terms` | 이용약관 |
| `/legal/privacy` | 개인정보처리방침 |
| `/legal/data-sources` | 데이터출처 |
| `/login`, `/register`, `/mypage` | 호환 라우트. 기본 UX는 우측 상단 계정 팝업 |

## 주요 API

| API | 용도 |
|---|---|
| `GET /api/search` | 지역/키워드 검색 |
| `GET /api/map/geojson/seoul-mask` | 서울 외곽 마스크 GeoJSON |
| `GET /api/map/transit-route` | 교통 경로 조회 |
| `GET /api/heatmap/geojson/adongs` | 행정동 GeoJSON |
| `GET /api/heatmap/geojson/ldongs` | 법정동 GeoJSON |
| `GET /api/heatmap/adongs/scores` | 행정동 점수 |
| `GET /api/heatmap/ldongs/scores` | 법정동 점수 |
| `POST /api/recommend/regions` | 조건 기반 행정동/법정동 추천 |
| `GET /api/amenities/bbox` | 지도 영역 내 편의시설 |
| `GET /api/medical/facilities` | 의료시설 목록 |
| `GET /api/medical/facilities/<hpid>` | 의료시설 상세 |
| `GET /api/medical/specialties` | 의료 진료과목 목록 |
| `GET /api/medical/specialty-groups` | 의료 진료과목 그룹 목록 |
| `GET /api/dashboard/cache` | 동네 정보 캐시 |
| `GET /api/dashboard/regions/adongs/lookup` | 좌표 기준 행정동 lookup |
| `GET /api/dashboard/regions/adongs/<slug>/intro` | 행정동 소개 |
| `GET /api/dashboard/regions/ldongs/lookup` | 좌표 기준 법정동 lookup |
| `GET /api/dashboard/regions/ldongs/<slug>/intro` | 법정동 소개 |
| `GET /api/dashboard/safety/crime-zone` | 생활안전지도 WMS 프록시 |
| `POST /api/rent-deals/listing-analysis` | 매물 분석 |
| `GET /api/rent-deals/conversion-rate` | 보증금-월세 환산율 |
| `POST /api/agent/query` | AI 질의 |
| `GET/POST /api/agent/api-keys` | AI API KEY 상태 조회/저장 |
| `POST /api/agent/api-keys/unlock` | 저장된 AI API KEY 잠금 해제 |
| `DELETE /api/agent/api-keys/<provider>` | AI API KEY 삭제 |
| `GET/PATCH /api/users/me` | 내 정보 조회/수정 |
| `GET /api/users/universities` | 대학 선택지 |
| `GET/PUT /api/users/me/candidate-regions` | 담은 동네 조회/저장 |
| `GET/PUT /api/users/me/recommendation-conditions` | 추천 조건 조회/저장 |
| `POST /api/auth/login` | 로그인 |
| `POST /api/auth/logout` | 로그아웃 |
| `GET /api/auth/kakao/start` | Kakao 로그인 시작 |
| `GET /api/auth/kakao/callback` | Kakao 로그인 callback |

## 초기 세팅

```bash
cd /home/ubuntu/capston
docker compose up -d db redis
docker compose build backend
docker compose run --rm backend python manage.py migrate
scripts/db/apply_agent_read_permissions.sh
docker compose up -d backend
docker compose ps
```

프론트엔드 개발:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

백엔드 개발:

```bash
cd backend
cp .env.example .env
uv venv --python 3.12
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e .
python manage.py migrate
python manage.py runserver
```

## 데이터 업데이트

기본 실행은 dry-run입니다. 실제 DB 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
```

운영 자동 업데이트는 systemd timer `capston-scheduled-update.timer`가 backend 컨테이너 안에서 `scripts/update/scheduled_update.py`를 실행하는 방식입니다. 상태 JSON은 `backend/scripts/update/.state` 아래에 저장됩니다.

## 운영 주의

- `.env`, DB 비밀번호, 개인 키는 Git에 기록하지 않습니다.
- `frontend/.env`의 `VITE_` 값은 클라이언트에 노출됩니다.
- 공공데이터 원천 DB 값은 마이그레이션/업데이트 정책에 맞춰서만 변경합니다.
- AI Agent DB 계정은 허용된 조회 테이블만 읽도록 제한합니다.
- 데이터출처와 법적 안내는 `/legal/data-sources`, `/legal/terms`, `/legal/privacy`에서 유지합니다.
