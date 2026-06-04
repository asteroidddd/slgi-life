# backend/scripts

자취맵 백엔드 데이터 업데이트와 검증을 위한 스크립트 모음입니다.

## 현재 구조

| 경로 | 역할 |
|---|---|
| `update/` | 공공데이터 및 서비스 파생 데이터 업데이트 실행 |
| `validate/` | 데이터 품질/스키마 검증 스크립트 위치 |

`etl/`, `maintenance/`, `scoring/` 같은 이전 스크립트 폴더는 현재 업데이트 흐름에 포함되지 않습니다. 이전 코드는 Git 이력에서 확인합니다.

## 업데이트 스크립트

| 파일 | 역할 |
|---|---|
| `update/scheduled_update.py` | systemd timer가 호출하는 운영용 스케줄러. 상태 JSON, 실행 조건, 재시도, 부분 실패 기록을 관리 |
| `update/update_all.py` | 공공데이터, 서비스 파생 데이터, 대시보드 캐시, 유지보수 작업을 전체 순서대로 실행 |
| `update/update_public_data.py` | 공공데이터 도메인을 하나씩 또는 전체 순서대로 업데이트 |
| `update/update_service_data.py` | 서비스 파생 데이터를 하나씩 또는 전체 순서대로 업데이트 |
| `update/update_dashboard_data.py` | 대시보드 화면 전용 데이터를 하나씩 또는 전체 순서대로 업데이트 |
| `update/update_cache_data.py` | 전월세 지오코딩, 지역별 공원/편의시설 집계 같은 운영 보조 캐시를 업데이트 |

기본은 dry-run이며 실제 DB 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
python scripts/update/update_dashboard_data.py --target all --write
python scripts/update/update_cache_data.py --target all --write
```

## 실행 순서

1. 공공데이터 업데이트
   - `regions`
   - `metrics`
   - `populations`
   - `rent_deals`
   - `univ`
   - `bus`
   - `subway`
   - `stores`
   - `medical`
   - `parks`
   - `library`
2. 서비스 파생 데이터 업데이트
   - `amenity`
   - `current`
3. 대시보드 데이터 업데이트
   - `dashboard_cache`
4. 유지보수 작업
   - `ai_stale_keys`

`update_cache_data.py`는 `update_all.py`에 포함되지 않는 선택 운영 캐시입니다. 필요할 때 별도로 실행합니다.

지원 target:

- `rent_deal_geocode_cache`
- `region_park_area_cache`
- `region_amenity_category_cache`

업데이트 상태 JSON은 `backend/scripts/update/.state` 아래에 저장됩니다. 운영에서는 이 경로를 Docker bind mount/volume으로 보존해야 컨테이너 재생성 후에도 업데이트 이력이 유지됩니다.

## 운영 메모

- 매일 자정 운영 실행은 systemd `capston-scheduled-update.timer`가 `scheduled_update.py --write`를 호출합니다.
- API 호출 제한, 네트워크 오류, 부분 실패가 반복되면 실패 상태를 기록하고 가능한 다음 작업은 계속 진행합니다.
- 스크립트 실행 전 `backend/.env`와 DB migration 상태를 확인합니다.
