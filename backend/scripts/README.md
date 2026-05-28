# backend/scripts

백엔드 데이터 업데이트와 검증을 위한 스크립트 모음입니다.

## 현재 구조

| 경로 | 역할 |
|---|---|
| `update/` | 공공데이터 및 서비스 파생 데이터 업데이트 실행 |
| `validate/` | 데이터 품질/스키마 검증 스크립트 위치 |

`etl/`, `maintenance/`, `scoring/` 같은 과거 스크립트 폴더는 새 업데이트 흐름에서 사용하지 않아 제거했습니다. 과거 코드가 필요하면 Git 이력에서 확인합니다.

## 업데이트 스크립트

| 파일 | 역할 |
|---|---|
| `update/update_all.py` | 공공데이터와 서비스 파생 데이터를 전체 순서대로 업데이트 |
| `update/update_public_data.py` | 공공데이터 도메인을 하나씩 또는 전체 순서대로 업데이트 |
| `update/update_service_data.py` | 서비스 파생 데이터를 하나씩 또는 전체 순서대로 업데이트 |

기본은 dry-run이며 실제 DB 반영에는 `--write`가 필요합니다.

```bash
cd /home/ubuntu/capston/backend
python scripts/update/update_all.py --write
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
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
   - `parks`
   - `library`
2. 서비스 파생 데이터 업데이트
   - `amenity`
   - `current`

업데이트 상태 JSON은 `backend/apps/public_data/.state` 아래에 저장됩니다.

## 운영 메모

- 매일 자정 실행이 필요하면 배포 환경의 cron 또는 CI/CD 스케줄러에서 `update_all.py --write`를 호출합니다.
- API 호출 제한, 네트워크 오류, 부분 실패가 발생하면 이후 단계는 중단하고 다음 실행에서 이어받습니다.
- 스크립트 실행 전 `backend/.env`와 DB migration 상태를 확인합니다.
