import { useNavigate } from 'react-router-dom';

type LegalPage = 'terms' | 'privacy' | 'data';

type LegalLink = {
  label: string;
  href: string;
};

type LegalTableRow = {
  category: string;
  source: string;
  usage: string;
  links: LegalLink[];
};

type LegalArticle = {
  title: string;
  paragraphs?: string[];
  items?: string[];
  rows?: LegalTableRow[];
};

type LegalContent = {
  title: string;
  updatedAt: string;
  lead: string;
  articles: LegalArticle[];
};

const CONTENT: Record<LegalPage, LegalContent> = {
  terms: {
    title: '이용약관',
    updatedAt: '2026년 5월 30일',
    lead: '이 약관은 자취맵 서비스 이용 조건, 서비스의 성격, 사용자와 운영자의 권리와 의무를 정합니다.',
    articles: [
      {
        title: '제1조 목적',
        paragraphs: [
          '이 약관은 자취맵이 제공하는 지도 기반 주거 탐색, 대시보드, 부동산 도우미, AI 질의 기능 및 관련 부가 기능의 이용 조건과 절차를 정하는 것을 목적으로 합니다.',
          '자취맵은 공공데이터와 사용자가 입력한 정보를 바탕으로 주거 탐색을 돕는 참고용 서비스를 제공합니다.',
        ],
      },
      {
        title: '제2조 용어의 정의',
        items: [
          '서비스: 자취맵 웹사이트와 그 안에서 제공되는 지도, 검색, 대시보드, 부동산 도우미, AI 질의, 계정 관리 기능을 말합니다.',
          '회원: 카카오 로그인을 통해 서비스에 접속하고, 서비스 이용을 위해 필요한 정보를 입력한 사용자를 말합니다.',
          '공공데이터: 공공데이터포털, 서울 열린데이터광장, V-World, KOSIS, 생활안전정보 등 외부 제공기관에서 제공하거나 이를 바탕으로 전처리한 데이터를 말합니다.',
          'AI 기능: 사용자가 입력한 질문과 서비스가 구성한 지역 맥락을 바탕으로 외부 AI 제공자에게 질의를 보내고 응답을 표시하는 기능을 말합니다.',
          'AI API 키: 사용자가 OpenAI 등 외부 AI 제공자 이용을 위해 직접 등록한 API 키를 말합니다.',
        ],
      },
      {
        title: '제3조 약관의 효력과 변경',
        items: [
          '이 약관은 서비스 화면에 게시하거나 연결된 페이지로 제공함으로써 효력이 발생합니다.',
          '운영자는 서비스 기능, 관련 법령, 운영 정책의 변경에 따라 약관을 수정할 수 있습니다.',
          '중요한 변경이 있는 경우 서비스 화면 또는 별도 공지 방식으로 안내합니다. 사용자가 변경 후에도 서비스를 계속 이용하면 변경 약관에 동의한 것으로 볼 수 있습니다.',
        ],
      },
      {
        title: '제4조 서비스의 내용',
        items: [
          '지역 검색, 주소 검색, 현재 위치 기반 지도 탐색',
          '전월세 실거래 기반 시세 요약, 환산월세 추이, 거래량 표시',
          '교통 접근성, 생활 인프라, 안전 지표 등 지역 대시보드',
          '매물 주소, 면적, 유형, 보증금, 월세를 입력받아 주변 거래와 비교하는 부동산 도우미',
          '사용자 설정과 지역 데이터를 바탕으로 답변을 생성하는 AI에게 묻기 기능',
          '회원 프로필, 집 위치, 즐겨찾기, AI API 키 관리 기능',
        ],
      },
      {
        title: '제5조 회원가입과 로그인',
        items: [
          '서비스 로그인은 카카오 로그인을 사용합니다.',
          '자취맵은 카카오 로그인에서 이메일 동의항목을 요청하지 않습니다. 서비스 안내와 계정 관리를 위한 이메일은 회원이 직접 입력합니다.',
          '회원은 본인의 정확한 정보를 입력해야 하며, 타인의 계정, 주소, API 키를 무단으로 사용할 수 없습니다.',
          '운영자는 허위 정보 입력, 부정 사용, 보안 위험이 확인된 계정의 이용을 제한할 수 있습니다.',
        ],
      },
      {
        title: '제6조 사용자의 의무',
        items: [
          '사용자는 서비스를 법령과 이 약관에 맞게 이용해야 합니다.',
          '서비스에서 얻은 정보를 불법 행위, 권리 침해, 자동화된 대량 수집, 원천 데이터 제공기관의 이용 조건을 위반하는 방식으로 사용할 수 없습니다.',
          '사용자는 계약, 보증금, 권리관계, 건축물 현황 등 중요한 사항을 서비스 결과만으로 판단하지 않고 원천 자료와 현장을 직접 확인해야 합니다.',
          '사용자는 AI 기능에 민감정보, 타인의 개인정보, 공개해서는 안 되는 계약 정보나 비밀 정보를 입력하지 않아야 합니다.',
        ],
      },
      {
        title: '제7조 데이터와 분석 결과의 성격',
        items: [
          '서비스의 지도, 시세, 거래량, 밀도, 점수, 순위, 안전 지도, 안내문은 모두 참고용 정보입니다.',
          '원천 데이터의 오류, API 장애, 갱신 지연, 좌표 오차, 행정구역 경계 차이, 전처리 방식에 따라 실제 현황과 다를 수 있습니다.',
          '대시보드의 서울 평균 비교는 서비스 DB에 적재된 서울 범위 데이터를 기준으로 계산합니다.',
          '부동산 도우미의 매물 분석은 법정동 또는 인접 지역의 과거 거래를 바탕으로 한 참고 지표이며, 감정평가, 중개 의견, 금융 자문, 법률 자문이 아닙니다.',
        ],
      },
      {
        title: '제8조 부동산 관련 확인 책임',
        items: [
          '사용자는 임대차 계약 전 등기부등본, 건축물대장, 전입세대 열람 가능 여부, 임대인 신원, 보증보험 가능 여부, 중개대상물 확인설명서 등을 별도로 확인해야 합니다.',
          '전월세 실거래 정보와 환산월세 계산은 거래 조건, 관리비, 옵션, 층, 방향, 준공연도, 수리 상태, 권리관계, 특약 등 개별 요소를 모두 반영하지 못할 수 있습니다.',
          '서비스의 외부 링크는 사용자의 추가 확인을 돕기 위한 것이며, 외부 사이트의 정보와 서비스 운영에 대한 책임은 각 제공자에게 있습니다.',
        ],
      },
      {
        title: '제9조 AI 기능과 API 키',
        items: [
          'AI 기능의 응답은 자동 생성 결과이며 부정확하거나 최신 정보가 아닐 수 있습니다.',
          '회원이 등록한 AI API 키는 회원 본인의 책임으로 관리해야 하며, 외부 AI 제공자의 요금, 한도, 정책은 해당 제공자의 기준을 따릅니다.',
          '서비스는 AI API 키를 암호화해 저장하고, 복호화 문구 없이는 서버 단독으로 원문 키를 사용할 수 없도록 설계합니다.',
          '사용자가 AI 기능을 이용하면 질문 내용, 선택 지역 정보, 사용자가 허용한 프로필 맥락이 외부 AI 제공자에게 전송될 수 있습니다.',
        ],
      },
      {
        title: '제10조 서비스 변경과 중단',
        items: [
          '운영자는 서비스 개선, 보안 조치, 데이터 구조 변경, 외부 API 장애, 배포 또는 점검을 위해 서비스의 전부 또는 일부를 변경하거나 중단할 수 있습니다.',
          '시험 운영 단계의 기능은 사전 안내 없이 표시 방식, 계산 방식, 제공 범위가 바뀔 수 있습니다.',
          '외부 API 제공기관의 정책 변경, 호출 제한, 장애가 발생하면 일부 정보가 비어 있거나 갱신되지 않을 수 있습니다.',
        ],
      },
      {
        title: '제11조 지식재산권과 이용 제한',
        items: [
          '서비스의 화면 구성, 코드, 전처리 로직, 자체 생성 문구와 편집물에 대한 권리는 운영자 또는 정당한 권리자에게 있습니다.',
          '공공데이터와 외부 API의 원천 권리는 각 제공기관에 있으며, 사용자는 해당 제공기관의 이용 조건을 함께 준수해야 합니다.',
          '운영자의 동의 없이 서비스를 복제, 크롤링, 대량 수집, 재판매, 상업적 데이터베이스 구축에 사용할 수 없습니다.',
        ],
      },
      {
        title: '제12조 책임의 제한',
        items: [
          '운영자는 고의 또는 중대한 과실이 없는 한 원천 데이터 오류, 외부 API 장애, 네트워크 문제, 사용자의 입력 오류로 발생한 손해에 책임을 지지 않습니다.',
          '운영자는 서비스 정보만을 근거로 한 계약 체결, 보증금 손실, 매물 선택, 통근 판단, 안전 판단 등 사용자의 최종 의사결정 결과를 보장하지 않습니다.',
          '사용자가 외부 링크, 외부 AI 제공자, 공공데이터 제공기관 서비스를 이용하면서 발생한 문제는 해당 서비스의 약관과 정책을 따릅니다.',
        ],
      },
      {
        title: '제13조 회원탈퇴와 이용 종료',
        items: [
          '회원은 마이페이지에서 회원탈퇴를 요청할 수 있습니다.',
          '회원탈퇴 시 계정, 프로필, 집 주소와 좌표, 즐겨찾기, 저장된 AI API 키 등 서비스 제공에 필요한 회원 관련 정보가 삭제됩니다.',
          '관계 법령상 보존이 필요한 정보가 있는 경우 해당 정보는 법령이 정한 기간 동안 분리 보관될 수 있습니다.',
        ],
      },
      {
        title: '제14조 준거법과 문의',
        paragraphs: [
          '이 약관은 대한민국 법령을 기준으로 해석합니다. 서비스와 관련한 문의는 운영자 이메일로 접수할 수 있습니다.',
          '문의처: hwang9973@dgu.ac.kr',
        ],
      },
    ],
  },
  privacy: {
    title: '개인정보처리방침',
    updatedAt: '2026년 5월 30일',
    lead: '자취맵은 서비스 제공에 필요한 최소 범위의 개인정보를 처리하며, 사용자가 직접 저장하거나 허용한 정보 중심으로 기능을 제공합니다.',
    articles: [
      {
        title: '제1조 개인정보 처리 목적',
        items: [
          '카카오 로그인 기반 회원 식별과 로그인 상태 유지',
          '이메일 직접 입력을 통한 계정 관리와 서비스 안내',
          '집 위치 이동, 집 마커 표시, 즐겨찾기 등 개인화 기능 제공',
          'AI API 키 저장, 잠금 해제, AI 질의 기능 제공',
          '서비스 장애 대응, 보안 점검, 부정 사용 방지, 회원탈퇴 처리',
        ],
      },
      {
        title: '제2조 처리하는 개인정보 항목',
        items: [
          '계정 정보: 카카오 회원 식별자, 카카오 닉네임, 서비스 내부 사용자 ID, 사용자가 직접 입력한 이메일',
          '프로필 정보: 닉네임, 학교, 입학연도 등 사용자가 저장한 정보',
          '주소와 위치 정보: 사용자가 저장한 집 주소, 지번 중심 좌표, 주소 지오코딩 상태와 오류 정보',
          '관심 지역 정보: 즐겨찾기한 행정동 또는 법정동',
          'AI 설정 정보: AI 제공자, 암호화된 AI API 키, 키 표시용 마스킹 값, AI 맥락 공유 설정',
          '서비스 이용 정보: 로그인 기록, 인증 토큰, 요청 시각, 오류 확인에 필요한 서버 로그',
        ],
      },
      {
        title: '제3조 개인정보 수집 방법',
        items: [
          '카카오 로그인 과정에서 카카오가 제공하는 회원 식별자와 닉네임을 받습니다.',
          '이메일, 학교, 입학연도, 집 주소, AI API 키, AI 맥락 공유 설정은 사용자가 서비스 화면에서 직접 입력하거나 저장합니다.',
          '주소 검색과 좌표 변환 과정에서 V-World API를 사용해 주소를 좌표로 변환할 수 있습니다.',
          '현재 위치는 브라우저 권한을 통해 지도 이동에 사용할 수 있으며, 사용자가 집 주소로 저장하지 않는 한 계정 정보로 저장하지 않습니다.',
        ],
      },
      {
        title: '제4조 카카오 로그인과 이메일',
        items: [
          '자취맵은 카카오 로그인 인가 요청에 이메일 동의항목을 포함하지 않습니다.',
          '카카오에서 이메일을 수집하지 않으므로, 서비스 운영에 필요한 이메일은 사용자가 직접 입력합니다.',
          '카카오 계정 연결 해제 또는 보안 이벤트가 전달되면 관련 계정 삭제 또는 연결 해제 처리를 수행할 수 있습니다.',
        ],
      },
      {
        title: '제5조 외부 서비스와 정보 전송',
        items: [
          '카카오: 로그인, 토큰 발급, 사용자 식별을 위해 카카오 인증 서버와 통신합니다.',
          'V-World: 주소 검색, 주소 좌표 변환, 배경지도 표시를 위해 사용합니다.',
          'OpenAI 또는 Mindlogic 등 AI 제공자: 사용자가 AI 기능을 이용할 때 질문, 선택 지역 정보, 사용자가 허용한 맥락 정보가 전송될 수 있습니다.',
          '공공데이터 API 제공기관: 서비스 서버가 지역 데이터 갱신을 위해 호출하며, 회원의 개인정보를 전송하지 않습니다.',
        ],
      },
      {
        title: '제6조 AI API 키 처리',
        items: [
          '사용자가 저장한 AI API 키는 암호화해 저장합니다.',
          '복호화 문구는 서버에 저장하지 않으며, 사용자가 입력한 복호화 문구 없이는 서버 단독으로 원문 키를 사용할 수 없습니다.',
          '복호화된 키는 일정 시간 동안만 서버 캐시에 보관되며, 로그아웃하면 잠금 처리됩니다.',
          '7일 이상 로그인 기록이 없는 계정의 저장된 AI API 키는 삭제 대상입니다.',
          '사용자는 언제든지 마이페이지에서 저장된 AI API 키를 삭제할 수 있습니다.',
        ],
      },
      {
        title: '제7조 개인정보 보유와 삭제',
        items: [
          '회원 정보와 저장 정보는 서비스 이용 기간 동안 보관합니다.',
          '회원탈퇴 시 계정, 프로필, 집 주소와 좌표, 즐겨찾기, 저장된 AI API 키 등 회원 관련 정보는 삭제됩니다.',
          '오류 대응과 보안 확인을 위한 로그는 운영상 필요한 기간 동안 보관할 수 있으며, 불필요해지면 삭제 또는 비식별 처리합니다.',
          '관계 법령상 보존이 필요한 정보가 있는 경우 해당 법령에서 정한 기간 동안 분리 보관할 수 있습니다.',
        ],
      },
      {
        title: '제8조 이용자의 권리',
        items: [
          '사용자는 마이페이지에서 이메일, 프로필, 집 주소, AI API 키, AI 맥락 공유 설정을 조회, 수정, 삭제할 수 있습니다.',
          '사용자는 회원탈퇴를 통해 계정 삭제를 요청할 수 있습니다.',
          '개인정보 열람, 정정, 삭제, 처리정지 요청은 운영자 이메일로 접수할 수 있습니다.',
          '운영자는 본인 확인과 서비스 운영 상태를 확인한 뒤 합리적인 범위에서 요청을 처리합니다.',
        ],
      },
      {
        title: '제9조 개인정보 보호 조치',
        items: [
          'AI API 키는 암호화해 저장하고, 복호화 문구를 서버에 저장하지 않습니다.',
          '인증이 필요한 API는 로그인된 사용자만 접근할 수 있도록 제한합니다.',
          '서비스 운영에 필요한 API 키와 비밀값은 환경 변수로 관리하며, 화면과 문서에 실제 키 값을 표시하지 않습니다.',
          '불필요한 개인정보 수집을 줄이기 위해 카카오 이메일 동의항목을 사용하지 않습니다.',
        ],
      },
      {
        title: '제10조 쿠키와 인증 토큰',
        paragraphs: [
          '서비스는 로그인 유지, 인증, 보안 확인을 위해 브라우저 저장소 또는 쿠키를 사용할 수 있습니다. 사용자는 브라우저 설정을 통해 쿠키 저장을 제한할 수 있으나, 이 경우 일부 기능이 정상 동작하지 않을 수 있습니다.',
        ],
      },
      {
        title: '제11조 개인정보처리방침 변경',
        items: [
          '이 방침은 서비스 기능, 데이터 처리 방식, 관련 법령 변경에 따라 수정될 수 있습니다.',
          '중요한 변경이 있으면 서비스 화면 또는 별도 공지 방식으로 안내합니다.',
        ],
      },
      {
        title: '제12조 개인정보 문의',
        paragraphs: [
          '개인정보 처리와 관련한 문의, 열람, 정정, 삭제 요청은 운영자 이메일로 접수할 수 있습니다.',
          '문의처: hwang9973@dgu.ac.kr',
        ],
      },
    ],
  },
  data: {
    title: '데이터 출처',
    updatedAt: '2026년 5월 30일',
    lead: '자취맵은 공공데이터 API, 공개 파일, 내부 전처리 파일을 조합해 지도와 대시보드 정보를 제공합니다.',
    articles: [
      {
        title: '주요 출처',
        rows: [
          {
            category: '지도·공간 기준',
            source: 'V-World, 국토교통부, 국가데이터처',
            usage: '배경지도, 검색, 좌표 변환, 행정동·법정동·자치구 경계 표시와 지역 매핑 기준으로 사용합니다. 지도 렌더링에는 Leaflet을 사용합니다.',
            links: [
              { label: 'WMTS API', href: 'https://www.vworld.kr/dev/v4dv_wmtsguide_s001.do' },
              { label: '검색 API', href: 'https://www.vworld.kr/dev/v4dv_search_s001.do' },
              { label: 'Geocoder API', href: 'https://www.vworld.kr/dev/v4dv_geocoderguide2_s001.do' },
              { label: '법정동 경계', href: 'https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?dsId=30603' },
              { label: '행정동 경계', href: 'https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?dsId=30017' },
              { label: '자치구 경계', href: 'https://www.vworld.kr/dtmk/dtmk_ntads_s002.do?dsId=30015' },
              { label: 'Leaflet', href: 'https://leafletjs.com/' },
            ],
          },
          {
            category: '전월세 시세',
            source: '공공데이터포털, 국토교통부, KOSIS, 한국부동산원',
            usage: '전월세 실거래와 전월세전환율을 활용해 환산월세, 월별 거래량, 시세 요약, 매물 분석을 계산합니다.',
            links: [
              { label: '아파트 전월세 API', href: 'https://www.data.go.kr/data/15126474/openapi.do' },
              { label: '오피스텔 전월세 API', href: 'https://www.data.go.kr/data/15126475/openapi.do' },
              { label: '단독/다가구 전월세 API', href: 'https://www.data.go.kr/data/15126472/openapi.do' },
              { label: '연립다세대 전월세 API', href: 'https://www.data.go.kr/data/15126473/openapi.do' },
              { label: '종합주택 전환율', href: 'https://stat.kosis.kr/statHtml_host/statHtml.do?orgId=408&tblId=DT_30404_N0010&dbUser=NSI_IN_408' },
              { label: '아파트 전환율', href: 'https://stat.kosis.kr/statHtml_host/statHtml.do?orgId=408&tblId=DT_30404_N0010&dbUser=NSI_IN_408' },
              { label: '연립/다세대 전환율', href: 'https://stat.kosis.kr/statHtml_host/statHtml.do?orgId=408&tblId=DT_30404_N0010&dbUser=NSI_IN_408' },
              { label: '단독주택 전환율', href: 'https://stat.kosis.kr/statHtml_host/statHtml.do?orgId=408&tblId=DT_30404_N0010&dbUser=NSI_IN_408' },
            ],
          },
          {
            category: '생활 인프라',
            source: '공공데이터포털, 소상공인시장진흥공단, 통계분류포털, 국가데이터처, 서울 열린데이터광장, 서울특별시, OpenStreetMap',
            usage: '상권 업종, 도서관, 대학, 공원 데이터를 묶어 식생활·문화·학습·공원·대학 관련 생활 인프라 밀도와 구성을 계산합니다.',
            links: [
              { label: '상가(상권)정보 API', href: 'https://www.data.go.kr/data/15012005/openapi.do' },
              { label: '제10차 한국표준산업분류', href: 'https://kssc.mods.go.kr:8443/ksscNew_web/index.jsp' },
              { label: '서울시 공공도서관 현황정보', href: 'https://data.seoul.go.kr/dataList/OA-15480/S/1/datasetView.do' },
              { label: '서울시 작은도서관 현황정보', href: 'https://data.seoul.go.kr/dataList/OA-15481/S/1/datasetView.do' },
              { label: '서울시 대학 및 전문대학 DB', href: 'https://data.seoul.go.kr/dataList/OA-12974/S/1/datasetView.do' },
              { label: 'OpenStreetMap', href: 'https://www.openstreetmap.org/#map=17/37.536266/126.984186' },
              { label: '생활권계획 시설(공원) 공간정보', href: 'https://data.seoul.go.kr/dataList/OA-15529/S/1/datasetView.do' },
              { label: '서울시 주요 공원현황', href: 'http://data.seoul.go.kr/dataList/OA-394/S/1/datasetView.do' },
            ],
          },
          {
            category: '의료',
            source: '공공데이터포털, 국립중앙의료원, 건강보험심사평가원',
            usage: '병원, 치과, 약국, 응급실, 명절 진료 운영, 진료과목 정보 표시',
            links: [
              { label: '전국 병·의원 찾기 서비스', href: 'https://www.data.go.kr/data/15000736/openapi.do' },
              { label: '전국 약국 정보 조회 서비스', href: 'https://www.data.go.kr/data/15000576/openapi.do' },
              { label: '의료기관별상세정보서비스', href: 'https://www.data.go.kr/data/15001699/openapi.do' },
              { label: '병원정보서비스', href: 'https://www.data.go.kr/data/15001698/openapi.do' },
              { label: '응급의료기관 API', href: 'https://www.data.go.kr/data/15000563/openapi.do' },
              { label: '명절 비상 진료기관 API', href: 'https://www.data.go.kr/data/15000480/openapi.do' },
            ],
          },
          {
            category: '교통 접근성',
            source: '공공데이터포털, 국토교통부, 서울 열린데이터광장, 서울특별시, 서울교통공사, 서울시메트로9호선',
            usage: '버스정류장, 지하철역, 버스 혼잡도, 지하철 혼잡도를 활용해 면적당 교통시설 밀도와 시간대별 혼잡 흐름을 표시합니다.',
            links: [
              { label: '버스정류장', href: 'https://www.data.go.kr/data/15142032/openapi.do' },
              { label: '서울시 버스정류소 위치정보', href: 'https://data.seoul.go.kr/dataList/OA-15067/S/1/datasetView.do' },
              { label: '노선별 혼잡도', href: 'https://www.data.go.kr/data/15142068/openapi.do' },
              { label: '서울시 역사마스터 정보', href: 'https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do' },
              { label: '지하철혼잡도', href: 'https://data.seoul.go.kr/dataList/OA-12928/A/1/datasetView.do' },
              { label: '9호선 혼잡도', href: 'https://data.seoul.go.kr/dataList/OA-22197/F/1/datasetView.do' },
            ],
          },
          {
            category: '인구·통계 지표',
            source: '공공데이터포털, KOSIS, 행정안전부, 소방청, 국토교통부, 경찰청, 국가데이터처, 한국부동산원, 한국국토정보공사',
            usage: '행정동·법정동 인구와 자치구 단위 안전·교통·경제·주거·환경 통계를 서울 평균 비교와 AI 질의 참고 지표로 사용합니다.',
            links: [
              { label: '행정동별 주민등록 인구', href: 'https://www.data.go.kr/data/15108065/openapi.do' },
              { label: '법정동별 주민등록 인구', href: 'https://www.data.go.kr/data/15108071/openapi.do' },
              { label: '지역안전등급', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20341&conn_path=I2' },
              { label: '화재발생건수', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL8601&conn_path=I2' },
              { label: '교통문화지수', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20331&conn_path=I2' },
              { label: '음주운전교통사고비율', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL14001&conn_path=I2' },
              { label: '뺑소니교통사고율', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL13901&conn_path=I2' },
              { label: '자동차천대당교통사고발생건수', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL21051&conn_path=I2' },
              { label: '자동차등록대수', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=110&tblId=DT_110001_A029&conn_path=I2' },
              { label: 'GRDP', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1C65_03E&conn_path=I2' },
              { label: '주택수', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=INH_1JU1501&conn_path=I2' },
              { label: '지가변동률', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20881E&conn_path=I2' },
              { label: '주민등록인구', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20651E&conn_path=I2' },
              { label: '고령인구비율', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20632&conn_path=I2' },
              { label: '청년인구비율', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL20643&conn_path=I2' },
              { label: '녹지율', href: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1YL202105E&conn_path=I2' },
            ],
          },
          {
            category: '안전 지도',
            source: '생활안전정보, 경찰청',
            usage: '안전 지도 레이어의 범죄주의구간 표시. CCTV 레이어는 현재 사용하지 않습니다.',
            links: [
              { label: '범죄주의구간(전체)', href: 'https://www.safemap.go.kr/opna/data/dataViewRenew.do?objtId=205' },
            ],
          },
          {
            category: 'AI 에이전트',
            source: 'mindlogic Docs, OpenAI',
            usage: 'AI 에이전트 응답을 위한 API 활용',
            links: [
              { label: 'mindlogic API Gateway', href: 'https://docs.mindlogic.ai/docs/general/gateway/getting-started/overview#api-gateway' },
              { label: 'OpenAI API', href: 'https://openai.com/ko-KR/index/openai-api/' },
            ],
          },
        ],
      },
      {
        title: '전처리와 한계',
        items: [
          '일부 데이터는 행정동·법정동 경계에 맞춰 공간 조인, 좌표 변환, 업종 매핑, 면적 대비 밀도 계산을 거칩니다.',
          '원천 API 장애, 제공기관 개편, 갱신 지연, 좌표 오차, 폐업/이전 반영 지연이 있을 수 있습니다.',
          '대시보드의 서울 평균 비교는 서비스 DB에 적재된 서울 범위 데이터를 기준으로 계산합니다.',
          '서비스 화면에 표시되는 데이터는 참고용이며, 계약·신고·법적 판단의 최종 근거가 아닙니다.',
        ],
      },
    ],
  },
};

export default function LegalInfo({ page }: { page: LegalPage }) {
  const navigate = useNavigate();
  const content = CONTENT[page];

  return (
    <main className="min-h-screen bg-primary-soft px-4 py-7 text-text sm:px-6 sm:py-8">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="app-floating-button fixed left-5 top-5 z-[1200] h-10 min-h-10"
      >
        뒤로가기
      </button>

      <article className="mx-auto max-w-[1040px] rounded-card border border-border bg-white p-6 shadow-sm sm:p-8">
        <header className="border-b border-divider pb-5">
          <p className="m-0 text-[12px] font-semibold text-text-subtle">최종 수정일: {content.updatedAt}</p>
          <h1 className="m-0 mt-3 text-[30px] font-bold text-text">{content.title}</h1>
          <p className="m-0 mt-3 text-[15px] leading-7 text-text-muted">{content.lead}</p>
        </header>

        <div className="mt-6 grid gap-8">
          {content.articles.map((article) => (
            <section key={article.title} className="grid gap-3">
              <h2 className="m-0 text-[18px] font-bold text-text">{article.title}</h2>

              {article.paragraphs ? (
                <div className="grid gap-2 text-[14px] leading-7 text-text-muted">
                  {article.paragraphs.map((paragraph) => (
                    <p key={paragraph} className="m-0">
                      {paragraph}
                    </p>
                  ))}
                </div>
              ) : null}

              {article.items ? (
                <ol className="m-0 grid list-none gap-2 p-0 text-[14px] leading-7 text-text-muted">
                  {article.items.map((item, index) => (
                    <li key={item} className="grid grid-cols-[28px_1fr] gap-2">
                      <span className="font-semibold text-text-subtle">{index + 1}.</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ol>
              ) : null}

              {article.rows ? (
                <div className="overflow-x-auto rounded-[8px] border border-border">
                  <table className="w-full min-w-[860px] border-collapse text-left text-[13px] leading-6">
                    <thead className="bg-surface-alt text-text">
                      <tr>
                        <th className="w-[130px] border-b border-border px-4 py-3 font-bold">구분</th>
                        <th className="w-[210px] border-b border-border px-4 py-3 font-bold">출처/제공</th>
                        <th className="border-b border-border px-4 py-3 font-bold">사용 내용</th>
                        <th className="w-[240px] border-b border-border px-4 py-3 font-bold">확인 링크</th>
                      </tr>
                    </thead>
                    <tbody>
                      {article.rows.map((row) => (
                        <tr key={row.category} className="border-b border-border last:border-b-0">
                          <td className="px-4 py-3 align-top font-semibold text-text">{row.category}</td>
                          <td className="px-4 py-3 align-top text-text-muted">{row.source}</td>
                          <td className="px-4 py-3 align-top text-text-muted">{row.usage}</td>
                          <td className="px-4 py-3 align-top">
                            <div className="grid gap-1">
                              {row.links.map((link) => (
                                <a
                                  key={`${row.category}-${link.href}`}
                                  href={link.href}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="block font-semibold text-primary hover:text-primary-hover"
                                >
                                  {link.label}
                                </a>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </section>
          ))}
        </div>

        {page === 'data' ? (
          <footer className="mt-8 flex justify-end border-t border-divider pt-5">
            <img
              src="/marks/img_opentype01.jpg"
              alt="공공누리 공공저작물 자유이용허락"
              className="h-auto w-[128px]"
              loading="lazy"
            />
          </footer>
        ) : null}
      </article>
    </main>
  );
}
