# DATA_SOURCES

Capston의 원천 데이터, 업데이트 정책, 프론트엔드 제공 API를 정리합니다. 파일 기반 데이터의 세부 출처는 `backend/data/DATA_SOURCES.md`를 함께 봅니다.

## 1. 데이터 업데이트 원칙

- 공공데이터 API 기반 데이터와 파일 기반 데이터가 함께 사용됩니다.
- 파일 기반 데이터는 `backend/data` 아래에 둡니다.
- 업데이트 상태 JSON은 `backend/apps/public_data/.state` 아래에 저장합니다.
- 기본 실행은 dry-run이며, 실제 반영에는 `--write`가 필요합니다.
- 실패, 부분 완료, 호출 제한이 발생하면 이후 업데이트 단계는 중단합니다.
- 삭제가 필요한 스냅샷성 데이터는 전체 적재가 성공한 뒤에만 삭제 반영합니다.
- 월/일 단위 데이터는 DB와 상태 JSON을 기준으로 누락 기간을 채우는 방식으로 이어받습니다.

## 2. 원천 데이터와 업데이트 정책

| 도메인 | 방식 | 주요 입력 | 주요 테이블 | 정책 |
|---|---|---|---|---|
| `regions` | 파일 | 행정구역 코드 CSV, 경계 GeoJSON | `gu`, `ldong`, `adong`, adjacency | 파일 해시 기반 스킵, 전체 갱신 |
| `metrics` | API/카탈로그 | KOSIS/지표 catalog | `metric`, `gu_metric`, `seoul_metric` | 삭제 없이 upsert |
| `populations` | API | 월별 인구 데이터 | `gu_population`, `ldong_population`, `adong_population` | 중간 누락 월 채움, 삭제 없음 |
| `rent_deals` | API + 파일 | 국토부 전월세 API, 법정동-행정동 매핑 CSV | `rent_deal`, `rent_deal_ldong_adong_map` | 201101부터 현재 월까지, 현재 월은 재적재 |
| `univ` | 파일 | `university_boundaries.geojson` | `univ`, mapping tables | 파일에서 사라진 항목 삭제 |
| `bus` | API | 버스정류장, 버스 혼잡도 API | `bus_stop`, `bus_congestion` | 혼잡도 최근 15일 기준, 누락분 보충 |
| `subway` | API + 파일 | 지하철 API, `subway_line9_congestion.xlsx` | `subway_station`, `subway_congestion`, `nearest_subway_*` | 스냅샷 기준 갱신, nearest cache 함께 갱신 |
| `stores` | API + 파일 | 소상공인 API, 업종분류 XLSX, KSIC XLSX | `store`, `business_category`, `ksic_category` | 전체 성공 시 삭제 반영 |
| `parks` | 파일 | `park_boundaries.geojson` | `park`, `park_adong`, `park_ldong` | 파일 해시 기반 스킵, 삭제 반영 |
| `library` | API | 도서관 API | `library`, `library_hours` | API 결과에서 사라진 도서관 삭제 |
| `amenity` | 파생 | store/park/library/univ/subway/bus | `amenity`, amenity mapping tables | 전체 재생성 |
| `current` | 파생 | rent/amenity/transit 원천 데이터 | `current_seoul`, `current_gu`, `current_ldong`, `current_adong` | 전체 재계산 |

## 3. 파일 기반 데이터

| 파일 | 용도 |
|---|---|
| `backend/data/gu_code.csv` | 자치구 코드 |
| `backend/data/adong_code.csv` | 행정동 코드 |
| `backend/data/ldong_code.csv` | 법정동 코드 |
| `backend/data/gu_boundaries.geojson` | 자치구 경계 |
| `backend/data/adong_boundaries.geojson` | 행정동 경계 |
| `backend/data/ldong_boundaries.geojson` | 법정동 경계 |
| `backend/data/store_business_category.xlsx` | 소상공인 업종분류 연계 |
| `backend/data/KSIC_10th.xlsx` | 한국표준산업분류 |
| `backend/data/subway_line9_congestion.xlsx` | 9호선 혼잡도 |
| `backend/data/park_boundaries.geojson` | 공원 경계 |
| `backend/data/university_boundaries.geojson` | 대학 경계 |
| `backend/data/rent_deal_ldong_adong_map.csv` | 법정동-행정동 매핑 |

## 4. API 키

실제 키 값은 문서에 기록하지 않습니다. 키 이름은 `backend/.env.example`과 운영 `backend/.env`를 기준으로 맞춥니다.

| 키 | 용도 |
|---|---|
| `PUBLIC_DATA_API_KEY` | 공공데이터포털 API |
| `PUBLIC_DATA_API_KEY2` | 공공데이터포털 보조 API 키 |
| `PUBLIC_DATA_API_KEY3` | 공공데이터포털 보조 API 키 |
| `PUBLIC_DATA_API_KEY4` | 공공데이터포털 보조 API 키 |
| `SEOUL_API_KEY` | 서울 열린데이터광장 API |
| `V_WORLD_API_KEY` | VWorld 주소/좌표 보정 |
| `KOSIS_API_KEY` | KOSIS 지표 API |
| `AI_AGENT_OPENAI_API_KEY` | AI Agent 기본 OpenAI API 키 |
| `AI_AGENT_OPENAI_BASE_URL` | AI Agent OpenAI 호환 base URL |
| `AI_AGENT_DATABASE_URL` | AI Agent 조회용 DB 연결 |

## 5. 업데이트 실행

전체 업데이트는 다음 명령으로 실행합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
```

개별 실행:

```bash
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
```

초기 세팅 시에는 migration이 먼저 적용되어 있어야 하며, `backend/.env`에 필요한 API 키가 들어 있어야 합니다. API 호출 제한이나 네트워크 오류가 발생하면 updater는 현재 실행을 중단하고, 다음 실행에서 DB와 상태 JSON을 기준으로 이어받습니다.

## 6. 현재 제공 API

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

과거 문서에 있던 `/api/adongs/*`, `/api/compare`, `/api/preference/*` 계열 API는 현재 활성 URL 라우팅에 포함되어 있지 않습니다.
