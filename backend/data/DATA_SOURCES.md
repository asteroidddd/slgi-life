## 데이터 소스

공공데이터 적재는 API 기반으로 처리하는 것을 원칙으로 합니다.

다만 API 기반 처리가 어려운 경우 data 폴더 내 파일 데이터를 기반으로 처리합니다.

| 파일 | 설명 | 출처 | 비고 |
|---|---|---|---|
| `data/gu_code.csv` | 서울시 자치구 코드 기준 파일 |  |  |
| `data/adong_code.csv` | 서울시 행정동 코드 기준 파일 |  | |
| `data/ldong_code.csv` | 서울시 법정동 코드 기준 파일 |  | |
| `data/gu_boundaries.geojson` | 서울시 자치구 경계 GeoJSON | [V-World 시군구 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30015&listPageIndex=1) | 서울시 데이터만 필터링, EPSG:4326 변환 |
| `data/adong_boundaries.geojson` | 서울시 행정동 경계 GeoJSON | [V-World 행정동 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30017&listPageIndex=1) | 서울시 데이터만 필터링, EPSG:4326 변환 |
| `data/ldong_boundaries.geojson` | 서울시 법정동 경계 GeoJSON | [V-World 법정동 SHP](https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?searchKeyword=&searchSvcCde=&searchOrganization=&searchBrmCode=&searchTagList=&searchFrm=&pageIndex=1&gidmCd=01&gidsCd=0102&sortType=00&svcCde=MK&dsId=30603&listPageIndex=1) | EPSG:4326 변환 |
| `data/store_business_category.xlsx` | 소상공인시장진흥공단 상권 업종분류 및 연계표 | [공공데이터포털 소상공인시장진흥공단 상가(상권)정보 API 첨부 파일](https://www.data.go.kr/data/15012005/openapi.do) | 파일 명, 시트 명 등 일부 수정 |
| `data/KSIC_10th.xlsx` | 제10차 한국표준산업분류표 | [국가데이터처 통계분류포털 한국표준산업분류 자료실](https://kssc.mods.go.kr:8443/ksscNew_web/kssc/main/main.do?gubun=1#) | 파일 명, 시트 명 등 일부 수정 |
| `data/subway_line9_congestion.xlsx` | 서울시 9호선 시간별 혼잡도 정보 | [서울 열린데이터광장 서울시 9호선 혼잡도 정보](https://data.seoul.go.kr/dataList/OA-22197/F/1/datasetView.do) | 파일 명 수정 |
| `data/park_boundaries.geojson` | 서울시 생활권계획 공원 시설 공간정보 GeoJSON | [서울 열린데이터광장 서울시 생활권계획 공원 시설 공간정보](https://data.seoul.go.kr/dataList/OA-15529/S/1/datasetView.do) | EPSG:4326 변환, 동일/포섭 경계 중복 38건 제거 |
| `data/university_boundaries.geojson` | 서울시 대학 캠퍼스 경계 GeoJSON | 기존 EC2 DB `univ` 테이블 | EPSG:4326, MultiPolygon |
| `data/rent_deal_ldong_adong_map.csv` | 전월세 실거래가 법정동-행정동 매핑 기준 파일 | 기존 EC2 DB `rent_deal_ldong_adong_map` 테이블 | 파일 명 수정 |

관련 데이터의 업데이트가 있을 시 양식에 맞춰 수정하면 됩니다.