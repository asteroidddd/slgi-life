# backend/scripts

백엔드 데이터 업데이트/검증용 스크립트 모음입니다.

## 현재 구조

| 경로 | 역할 |
|---|---|
| `update/` | 공공데이터 및 서비스 파생 데이터 업데이트 실행 |
| `validate/` | 검증 스크립트 자리 |

`etl/`, `maintenance/`, `scoring/`은 새 업데이트 흐름에서 사용하지 않아 제거했습니다. 과거 코드가 필요하면 git 이력에서 확인합니다.

## 업데이트 스크립트 상태

| 파일 | 상태 |
|---|---|
| `update/update_all.py` | 공공데이터와 서비스 파생 데이터를 전체 순서대로 업데이트 |
| `update/update_public_data.py` | 공공데이터 도메인을 하나씩 또는 전체 순서대로 업데이트 |
| `update/update_service_data.py` | 서비스 파생 데이터를 하나씩 또는 전체 순서대로 업데이트 |

기본은 dry-run이며 실제 반영에는 `--write`가 필요합니다.

```bash
python scripts/update/update_all.py --write
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
```

## 목표 실행 순서

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

매일 자정 실행은 배포 환경의 cron 또는 CI/CD 스케줄러에서 `update_all.py --write`를 호출하도록 구성합니다.
