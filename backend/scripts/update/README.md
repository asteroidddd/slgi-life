# scripts/update

데이터 업데이트 실행 스크립트입니다. 공공데이터 원천 테이블과 서비스 파생 테이블을 현재 코드의 도메인 순서에 맞게 갱신합니다.

## 현재 사용

| 파일 | 역할 |
|---|---|
| `update_all.py` | 공공데이터, 서비스 파생 데이터, 대시보드 캐시, 유지보수 작업을 정해진 순서로 실행 |
| `update_public_data.py` | 공공데이터 원천 테이블 업데이트 |
| `update_service_data.py` | `Amenity`, `Current*` 같은 서비스 파생 테이블 업데이트 |
| `update_dashboard_data.py` | 대시보드 화면 전용 캐시 업데이트 |

## 실행 예시

```bash
cd /home/ubuntu/capston/backend

# 전체 dry-run
python scripts/update/update_all.py

# 전체 실제 반영
python scripts/update/update_all.py --write

# 공공데이터만 실제 반영
python scripts/update/update_public_data.py --dataset all --write

# 서비스 파생 데이터만 실제 반영
python scripts/update/update_service_data.py --target all --write

# 대시보드 캐시만 실제 반영
python scripts/update/update_dashboard_data.py --target all --write
```

## 데이터 흐름

1. `update_public_data.py`가 원천 데이터를 갱신합니다.
2. `update_service_data.py`가 화면/API 제공에 필요한 파생 데이터를 재계산합니다.
3. `update_dashboard_data.py`가 대시보드 화면 전용 데이터를 갱신합니다.
4. `update_all.py`가 세 단계 이후 오래된 AI API 키 정리(`ai_stale_keys`)를 실행합니다.

## 주의

- 기본 실행은 dry-run입니다. DB에 반영하려면 반드시 `--write`를 붙입니다.
- 장시간 실행될 수 있으므로 운영에서는 로그와 실패 알림을 함께 구성합니다.
- API 호출 제한이나 네트워크 오류가 발생하면 해당 실행을 중단하고 다음 실행에서 이어받습니다.
- `fetch_*` 레거시 스크립트는 새 도메인별 업데이터로 대체되어 제거되었습니다.
