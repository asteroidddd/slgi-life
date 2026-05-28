# 데이터 소스

공공데이터 적재는 API 기반으로 처리하는 것을 원칙으로 합니다. API 기반 처리가 어렵거나 고정 기준 파일이 필요한 경우 `backend/data` 폴더의 파일 데이터를 사용합니다.

## 파일 기반 데이터

| 파일 | 설명 | 출처 | 비고 |
|---|---|---|---|
| `data/gu_code.csv` | 서울시 자치구 코드 기준 파일 | 프로젝트 기준 파일 | 서비스 행정구역 기준 |
| `data/adong_code.csv` | 서울시 행정동 코드 기준 파일 | 프로젝트 기준 파일 | 서비스 행정동 기준 |
| `data/ldong_code.csv` | 서울시 법정동 코드 기준 파일 | 프로젝트 기준 파일 | 전월세/지도 매핑 기준 |
| `data/gu_boundaries.geojson` | 서울시 자치구 경계 GeoJSON | [V-World 시군구 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30015&listPageIndex=1) | 서울시 데이터만 필터링, EPSG:4326 변환 |
| `data/adong_boundaries.geojson` | 서울시 행정동 경계 GeoJSON | [V-World 행정동 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30017&listPageIndex=1) | 서울시 데이터만 필터링, EPSG:4326 변환 |
| `data/ldong_boundaries.geojson` | 서울시 법정동 경계 GeoJSON | [V-World 법정동 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30603&listPageIndex=1) | EPSG:4326 변환 |
| `data/store_business_category.xlsx` | 소상공인시장진흥공단 상권 업종분류 및 연계표 | [공공데이터포털 소상공인시장진흥공단 상가(상권)정보 API 첨부 파일](https://www.data.go.kr/data/15012005/openapi.do) | 파일명과 시트명을 프로젝트 기준에 맞게 정리 |
| `data/KSIC_10th.xlsx` | 제10차 한국표준산업분류표 | [통계분류포털 한국표준산업분류 자료실](https://kssc.mods.go.kr:8443/ksscNew_web/kssc/main/main.do?gubun=1#) | 파일명과 시트명을 프로젝트 기준에 맞게 정리 |
| `data/subway_line9_congestion.xlsx` | 서울시 9호선 시간별 혼잡도 정보 | [서울 열린데이터광장 서울시 9호선 혼잡도 정보](https://data.seoul.go.kr/dataList/OA-22197/F/1/datasetView.do) | 파일명 수정 |
| `data/park_boundaries.geojson` | 서울시 생활권계획 공원 시설 공간정보 GeoJSON | [서울 열린데이터광장 서울시 생활권계획 공원 시설 공간정보](https://data.seoul.go.kr/dataList/OA-15529/S/1/datasetView.do) | EPSG:4326 변환, 동일/포섭 경계 중복 38건 제거 |
| `data/university_boundaries.geojson` | 서울시 대학 캠퍼스 경계 GeoJSON | 기존 EC2 DB `univ` 테이블 | EPSG:4326, MultiPolygon |
| `data/rent_deal_ldong_adong_map.csv` | 전월세 실거래가 법정동-행정동 매핑 기준 파일 | 기존 EC2 DB `rent_deal_ldong_adong_map` 테이블 | 파일명 수정 |

## 관리 원칙

- 파일을 교체하면 관련 updater가 파일 해시 또는 DB 상태를 기준으로 재적재 여부를 판단합니다.
- 출처, 전처리 방식, 파일명 변경 내역이 바뀌면 이 문서를 함께 수정합니다.
- 원천 파일 자체에 API 키, DB 접속 정보, 개인 키 등 비밀값을 넣지 않습니다.
- 대용량 원천 파일을 추가하기 전에는 Git 포함 여부와 배포 방식이 적절한지 확인합니다.
