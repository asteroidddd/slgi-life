# Capston

서울에서 자취를 준비하는 사용자가 동네별 주거비, 생활 편의, 교통 조건을 함께 비교할 수 있도록 돕는 공공데이터 기반 동네 탐색 서비스입니다.

## 서비스 개요

Capston은 서울 행정동을 기본 단위로 다룹니다. 사용자는 지도와 상세 화면에서 동네별 점수를 확인하고, 여러 동네를 비교하며, 자신의 선호에 맞는 자취 후보지를 찾을 수 있습니다.

핵심 판단 축은 다음 세 가지입니다.

| 축 | 의미 |
|---|---|
| Rent | 주거 비용 부담 |
| Amenity | 생활 편의시설 접근성 |
| Transit | 지하철/버스 접근성 |

## 주요 기능

- 행정동 지도 기반 동네 탐색
- 동네별 rent, amenity, transit 점수와 종합 점수 제공
- 동네 상세 화면에서 월세, 편의시설, 교통, 인구, 구 단위 지표 제공
- 여러 동네 비교
- 사용자 선호 기반 가중치 적용
- 로그인 사용자의 선호 설정과 즐겨찾기 관리
- AI Agent를 통한 자연어 질의 보조

## 주요 화면

| 화면 | 목적 |
|---|---|
| `/` | 지도 기반 동네 탐색 |
| `/dashboard` | 선택 동네의 지표형 대시보드 |
| `/dong/:slug` | 동네 상세 정보 |
| `/dong/:slug/explore` | 조건 기반 탐색 |
| `/compare` | 동네 비교 |
| `/login`, `/register`, `/mypage` | 사용자 계정과 개인화 |
| `/design-system` | 개발/디자인 확인용 화면 |

## 기술 스택

| 영역 | 내용 |
|---|---|
| Backend | Django, DRF, GeoDjango |
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
│   │   ├── public_data/      # 공공데이터 원천 테이블과 업데이터
│   │   ├── service/          # 화면 응답, 점수, 편의시설, 선호 기능
│   │   ├── ai_agent/         # 자연어 질의 보조
│   │   └── web/              # 사용자/인증
│   ├── data/                 # 파일 기반 원천 데이터
│   └── scripts/
│       ├── update/           # 데이터 업데이트 실행기
│       └── db/               # DB 운영 보조 스크립트
├── frontend/
│   ├── src/
│   │   ├── routes/           # 페이지 라우트
│   │   ├── components/       # 화면/도메인/UI 컴포넌트
│   │   ├── hooks/            # API 호출과 화면 상태 hook
│   │   ├── lib/              # API client, 유틸, 계산 보조
│   │   ├── contexts/         # 인증/전역 상태
│   │   ├── styles/           # 전역 스타일과 디자인 토큰
│   │   └── types/            # 프론트엔드 타입
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── initial_setup.sh          # 최초 수동 세팅 진입점
└── DATA_SOURCES.md
```

## 환경 파일

운영 환경 값은 Git에 포함하지 않습니다.

| 파일 | 용도 |
|---|---|
| `backend/.env` | Django, DB, Redis, 외부 API 키, AI Agent 설정 |
| `frontend/.env` | 프론트엔드 API 주소와 지도 키 |

루트 `.env`는 사용하지 않습니다.

Backend에 필요한 외부 API 키 이름은 `backend/.env.example`과 `DATA_SOURCES.md`를 기준으로 맞춥니다.

Frontend 주요 환경변수:

| 키 | 용도 |
|---|---|
| `VITE_API_BASE_URL` | 프론트엔드가 호출할 백엔드 API base URL |
| `VITE_VWORLD_API_KEY` | VWorld 지도 타일 키 |
| `VITE_KAKAO_JS_KEY` | Kakao JavaScript SDK 키 |

Vite는 `VITE_` prefix가 붙은 값만 클라이언트 번들에 노출합니다.

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

초기 세팅 전에는 `backend/.env`, `frontend/.env`, `docker-compose.yml`이 현재 서버 환경에 맞는지 확인해야 합니다.

## Backend

Backend는 Django/DRF/GeoDjango 기반입니다. 공공데이터 원천 테이블, 서비스 응답 API, 사용자 기능, AI Agent 기능을 함께 제공합니다.

주요 앱:

| 앱 | 역할 |
|---|---|
| `apps.public_data` | 공공데이터 API와 파일에서 가져온 원천 데이터 |
| `apps.service.amenities` | 화면 응답에 쓰기 쉬운 통합 편의시설 데이터 |
| `apps.service.scoring` | 현재 점수 테이블과 재계산 로직 |
| `apps.service.neighborhoods` | 동네 점수, 상세, 비교 API |
| `apps.service.preference` | 사용자 선호 학습과 가중치 관리 |
| `apps.ai_agent` | 자연어 질의 기반 보조 기능 |
| `apps.web.users` | 인증, 사용자, 즐겨찾기 |

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

Frontend는 React/Vite/TypeScript 기반 SPA입니다. 지도, 동네 상세, 대시보드, 비교, 로그인/마이페이지 화면을 제공합니다.

주요 폴더:

| 경로 | 역할 |
|---|---|
| `frontend/src/routes` | `MainMap`, `Dashboard`, `AdongDetail`, `AdongExplore`, `Compare`, 계정 화면 |
| `frontend/src/components/Map` | 지도, 히트맵, 사이드 패널, 범례 |
| `frontend/src/components/Dashboard` | 대시보드 위젯과 섹션 |
| `frontend/src/components/Detail` | 동네 상세 화면 섹션 |
| `frontend/src/components/ui` | 공통 UI 컴포넌트 |
| `frontend/src/hooks` | TanStack Query 기반 API hook |
| `frontend/src/lib` | API client, 지도/점수/계산 유틸 |
| `frontend/src/contexts` | 인증 등 전역 context |
| `frontend/src/styles` | 전역 스타일과 토큰 |

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

프론트엔드 API 연결은 `VITE_API_BASE_URL`을 기준으로 합니다. 운영 배포에서는 프론트엔드가 접근 가능한 백엔드 API 주소로 설정해야 합니다.

## 점수 체계

서비스 점수는 `service.scoring`의 `current_*` 테이블을 기준으로 제공합니다.

| 점수 | 기준 데이터 | 의미 |
|---|---|---|
| `score_rent` | `rent_deal` | 환산 월세가 낮을수록 높은 점수 |
| `score_amenity` | `amenity`, `park` 등 | 생활/의료/공원 접근성이 좋을수록 높은 점수 |
| `score_transit` | `nearest_subway_*`, `bus_stop` | 지하철과 버스 접근성이 좋을수록 높은 점수 |
| composite score | 세 점수의 가중합 | 사용자 가중치가 반영된 종합 점수 |

`current_seoul`, `current_gu`, `current_ldong`, `current_adong`은 같은 산식을 서로 다른 행정 단위에 적용한 파생 데이터입니다.

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

운영 자동화는 별도 스케줄러에서 `update_all.py --write`를 호출하는 방식으로 구성합니다. 장시간 실행 방지, 실패 시 다음 실행에서 이어받기, API 호출 제한 대응은 각 업데이터와 전체 실행기에서 관리합니다.

## 주요 문서

| 문서 | 용도 |
|---|---|
| `DATA_SOURCES.md` | 원천 데이터, 업데이트 정책, 프론트엔드 제공 API |
| `backend/data/DATA_SOURCES.md` | 파일 기반 데이터의 세부 출처 |
| `backend/scripts/README.md` | 업데이트 스크립트 개요 |

## 운영 주의

- `.env` 값은 문서나 Git에 기록하지 않습니다.
- 마이그레이션 적용 후 데이터 업데이트를 수행합니다.
- 공공데이터 API 호출 제한이 발생하면 해당 실행에서 중단하고 다음 실행에서 이어받습니다.
- 삭제가 필요한 스냅샷성 데이터는 전체 적재 성공 후에만 삭제 반영합니다.
- AI Agent DB 계정은 허용된 조회 테이블만 읽을 수 있도록 권한을 제한합니다.
- Frontend 환경변수 중 `VITE_` prefix 값은 클라이언트에 노출되므로 비밀값을 넣지 않습니다.
