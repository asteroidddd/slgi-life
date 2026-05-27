# 슬기로운 자취생활 — 백엔드

Django + DRF + GeoDjango (PostgreSQL/PostGIS).

## 사전 요구

- Python 3.12 (uv가 자동 설치)
- Docker (PostgreSQL/PostGIS 컨테이너)
- macOS Homebrew: `brew install gdal geos proj`
- `uv`: `brew install uv`

## 빠른 시작

```bash
# 1) 루트에서 DB + Redis 컨테이너
cd /Users/bagjihyeon/Desktop/School/capston
docker compose up -d

# 2) 백엔드 폴더로 이동
cd backend

# 3) 가상환경 + 의존성
uv venv --python 3.12
VIRTUAL_ENV="$(pwd)/.venv" uv pip install -e .

# 4) .env 생성 (이미 있으면 스킵)
cp .env.example .env

# 5) 마이그레이션 + 더미 시드
.venv/bin/python manage.py migrate

# 6) 개발 서버
.venv/bin/python manage.py runserver
```

## 동작 확인

```bash
# 기본 가중치 (33/33/34)
curl 'http://localhost:8000/api/dongs/scores' | python3 -m json.tool

# 교통 가중치 강조
curl 'http://localhost:8000/api/dongs/scores?w_rent=10&w_amenity=10&w_transit=80' | python3 -m json.tool

# 가중치 합 != 100 → 400
curl -i 'http://localhost:8000/api/dongs/scores?w_rent=50&w_amenity=50&w_transit=50'
```

응답 형식 (한 항목):
```json
{
  "slug": "hoegidong",
  "name": "회기동",
  "gu": "동대문구",
  "score": 71.55,
  "lat": 37.5917,
  "lng": 127.0533
}
```

## 폴더 구조

```
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
│   ├── users/         # 커스텀 User 모델
│   └── neighborhoods/ # Dong 모델 + /api/dongs/scores
└── .env.example
```

## 데이터 업데이트

실제 공공데이터와 서비스 파생 데이터는 업데이트 스크립트로 갱신합니다.

```bash
cd backend
.venv/bin/python scripts/update/update_all.py --write
```

## GDAL 트러블슈팅 (macOS)

Django 5.1은 GDAL 3.0~3.8을 자동 탐지하지만 우리는 3.12를 씁니다. `.env`에:

```
GDAL_LIBRARY_PATH=/opt/homebrew/opt/gdal/lib/libgdal.dylib
GEOS_LIBRARY_PATH=/opt/homebrew/opt/geos/lib/libgeos_c.dylib
```

Linux에서는 보통 비워둬도 됩니다.

## 향후 단계

- 5단계: `/api/dongs/:slug/summary` 추가
- 6단계: `/api/dongs/:slug/detail`
- 7단계: `/api/preference/{pairs,submit}` (scipy.optimize)
- 8단계: `/api/compare`
- 9단계: 카카오 로그인은 현재 비활성화 유지
- 실제 데이터 갱신: `scripts/update/update_all.py --write`
