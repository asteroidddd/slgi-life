# scripts/update

데이터 업데이트 실행 스크립트입니다.

## 현재 사용

| 파일 | 역할 |
|---|---|
| `update_all.py` | 공공데이터와 서비스 파생 데이터를 정해진 순서로 전체 업데이트 |
| `update_public_data.py` | 공공데이터 원천 테이블 업데이트 |
| `update_service_data.py` | `Amenity`, `Current*` 같은 서비스 파생 테이블 업데이트 |

```bash
python scripts/update/update_all.py --write
python scripts/update/update_public_data.py --dataset all --write
python scripts/update/update_service_data.py --target all --write
```

`fetch_*` 레거시 스크립트는 새 도메인별 업데이터로 대체되어 제거되었습니다.
