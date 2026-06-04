import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import courtLogo from '@/assets/logos/real-estate/court.png';
import dabangLogo from '@/assets/logos/real-estate/dabang.png';
import govSymbolLogo from '@/assets/logos/real-estate/gov-symbol.png';
import hugLogo from '@/assets/logos/real-estate/hug.png';
import kbLandLogo from '@/assets/logos/real-estate/kb-land.png';
import naverPayLogo from '@/assets/logos/real-estate/naver-pay.png';
import rebLogo from '@/assets/logos/real-estate/reb.png';
import seoulLogo from '@/assets/logos/real-estate/seoul.png';
import zigbangLogo from '@/assets/logos/real-estate/zigbang.png';
import { analyzeRentListing } from '@/features/common/lib/api';
import type { RentListingAnalysisResponse, RentListingType } from '@/features/common/types/api';

export type RealEstateHelperTab = 'checklist' | 'analysis' | 'links';
type RealEstateLink = {
  logoSrc: string;
  logoAlt: string;
  title: string;
  description: string;
  href: string;
  fillFrame?: boolean;
};

function parseHelperTab(value: string | null): RealEstateHelperTab {
  if (value === 'analysis' || value === 'links') return value;
  return 'checklist';
}

export default function RealEstatePage() {
  const [searchParams] = useSearchParams();
  const requestedTab = parseHelperTab(searchParams.get('tab'));
  const requestedAddress = searchParams.get('address')?.trim() ?? '';
  const [activeTab, setActiveTab] = useState<RealEstateHelperTab>(requestedTab);
  const [listingAddress, setListingAddress] = useState(requestedAddress || '서울특별시 관악구 신림동');
  const [listingDeposit, setListingDeposit] = useState(1000);
  const [listingMonthly, setListingMonthly] = useState(65);
  const [listingAreaM2, setListingAreaM2] = useState(20);
  const [listingType, setListingType] = useState<RentListingType>('villa_house');
  const [listingIncludeAdjacent, setListingIncludeAdjacent] = useState(false);
  const [listingAnalysis, setListingAnalysis] = useState<RentListingAnalysisResponse | null>(null);
  const [listingAnalysisError, setListingAnalysisError] = useState('');
  const [listingAnalysisLoading, setListingAnalysisLoading] = useState(false);

  useEffect(() => {
    setActiveTab(requestedTab);
    if (requestedAddress) setListingAddress(requestedAddress);
  }, [requestedAddress, requestedTab]);

  useEffect(() => {
    setListingAnalysis(null);
    setListingAnalysisError('');
  }, [listingAddress, listingAreaM2, listingType, listingDeposit, listingMonthly, listingIncludeAdjacent]);

  const handleListingAnalysis = async () => {
    setListingAnalysisLoading(true);
    setListingAnalysisError('');
    try {
      const result = await analyzeRentListing({
        address: listingAddress,
        area_m2: listingAreaM2,
        housing_type: listingType,
        deposit: listingDeposit,
        monthly_rent: listingMonthly,
        include_adjacent: listingIncludeAdjacent,
      });
      setListingAnalysis(result);
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string; address?: string[] | string } } })?.response?.data;
      const message = Array.isArray(detail?.address) ? detail.address[0] : detail?.address || detail?.detail;
      setListingAnalysisError(message || '매물 분석에 실패했습니다. 입력값을 확인해 주세요.');
    } finally {
      setListingAnalysisLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-primary-soft text-text">
      <section className="mx-auto grid w-full max-w-[1120px] gap-5 px-5 pb-12 pt-20 sm:px-8">
        <div>
          <h1 className="m-0 text-[32px] font-semibold leading-tight tracking-normal sm:text-section-heading">
            부동산 도우미
          </h1>
          <p className="m-0 mt-3 max-w-[760px] text-[14px] leading-6 text-text-muted">
            계약 전 확인할 것, 매물 가격 판단, 필요한 외부 사이트를 한 화면에서 봅니다.
          </p>
        </div>

        <article className="grid min-h-[720px] grid-cols-[220px_minmax(0,1fr)] overflow-hidden rounded-sm border border-border bg-surface/95 text-text shadow-floating" aria-label="부동산 도우미">
          <nav className="border-r border-border bg-surface-alt/80 p-3" aria-label="부동산 도우미 메뉴">
            {([
              ['checklist', '체크리스트', '계약 전 빠뜨리면 안 되는 확인 항목'],
              ['analysis', '매물 분석', '실거래 기반 가격 비교'],
              ['links', '외부 링크', '시세, 등기, 보증, 공공 정보'],
            ] as Array<[RealEstateHelperTab, string, string]>).map(([tab, label, description]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`mb-2 grid w-full gap-1 rounded-sm border px-3 py-3 text-left transition last:mb-0 ${
                  activeTab === tab
                    ? 'border-primary bg-surface text-primary shadow-sm'
                    : 'border-transparent text-text-muted hover:border-border hover:bg-surface'
                }`}
              >
                <strong className="text-[14px]">{label}</strong>
                <span className="text-[11px] leading-4">{description}</span>
              </button>
            ))}
          </nav>

          <div className="overflow-y-auto p-5">
            {activeTab === 'checklist' ? <RealEstateChecklist /> : null}
            {activeTab === 'analysis' ? (
              <RealEstateListingAnalysis
                address={listingAddress}
                areaM2={listingAreaM2}
                listingType={listingType}
                deposit={listingDeposit}
                monthlyRent={listingMonthly}
                includeAdjacent={listingIncludeAdjacent}
                analysis={listingAnalysis}
                loading={listingAnalysisLoading}
                error={listingAnalysisError}
                onAddressChange={setListingAddress}
                onAreaM2Change={setListingAreaM2}
                onListingTypeChange={setListingType}
                onDepositChange={setListingDeposit}
                onMonthlyRentChange={setListingMonthly}
                onIncludeAdjacentChange={setListingIncludeAdjacent}
                onAnalyze={handleListingAnalysis}
              />
            ) : null}
            {activeTab === 'links' ? <RealEstateLinks /> : null}
          </div>
        </article>
      </section>
    </main>
  );
}

export function RealEstateChecklist() {
  return (
    <div className="grid gap-3">
      <ChecklistCard title="계약 전" hint="가격과 권리관계를 먼저 확인합니다." items={[
        '국토교통부 실거래가와 주변 매물로 보증금·월세가 과하지 않은지 확인',
        '등기부등본으로 소유자, 근저당, 가압류, 압류, 가처분 확인',
        '다가구·단독주택이면 전입세대와 선순위 보증금 규모 확인',
        '임대인 국세·지방세 체납 여부 확인 요청',
        '건축물대장으로 위반건축물, 용도, 면적이 계약 내용과 맞는지 확인',
        '신탁등기가 있으면 신탁사 동의와 임대 권한 확인',
        'HUG 등 전세보증금 반환보증 가입 가능 여부 확인',
      ]} />
      <ChecklistCard title="계약 당일" hint="계약서와 당사자 정보를 맞춥니다." items={[
        '임대인 신분증과 등기부상 소유자 일치 확인',
        '대리인 계약이면 위임장, 인감증명서, 임대인 직접 연락 확인',
        '공인중개사 등록 상태, 자격증, 중개사무소 정보, 공제증서 확인',
        '계약금 입금 계좌가 임대인 명의인지 확인',
        '잔금 다음 날까지 권리 변동 금지 특약 넣기',
        '보증보험 가입 협조, 위반건축물·체납·선순위 권리 고지 특약 넣기',
      ]} />
      <ChecklistCard title="잔금과 입주 후" hint="대항력과 보증 안전장치를 마무리합니다." items={[
        '잔금 직전 등기부등본 재발급 후 권리 변동 확인',
        '입주 즉시 전입신고와 확정일자 처리',
        '전월세 계약 신고 대상이면 신고 완료 여부 확인',
        '보증보험 가입 완료와 보증서 발급 확인',
        '보증금을 돌려받기 전 전출하지 말고, 필요하면 임차권등기명령 검토',
      ]} />
    </div>
  );
}

function ChecklistCard({ title, hint, items }: { title: string; hint: string; items: string[] }) {
  return (
    <section className="border-t border-border pt-3 first:border-t-0 first:pt-0">
      <strong className="block text-[15px] text-primary">{title}</strong>
      <span className="mt-1 block text-[12px] leading-5 text-text-muted">{hint}</span>
      <ul className="m-0 mt-2 grid gap-1.5 p-0">
        {items.map((item, index) => {
          const id = `realestate-check-${title}-${index}`;
          return (
            <li key={item} className="grid grid-cols-[18px_1fr] items-start gap-2 text-[13px] leading-5 text-text-muted">
              <input id={id} type="checkbox" className="peer mt-0.5 h-[15px] w-[15px] accent-primary" />
              <label htmlFor={id} className="cursor-pointer peer-checked:text-text-subtle">{item}</label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function RealEstateListingAnalysis({
  address,
  areaM2,
  listingType,
  deposit,
  monthlyRent,
  includeAdjacent,
  analysis,
  loading,
  error,
  onAddressChange,
  onAreaM2Change,
  onListingTypeChange,
  onDepositChange,
  onMonthlyRentChange,
  onIncludeAdjacentChange,
  onAnalyze,
}: {
  address: string;
  areaM2: number;
  listingType: RentListingType;
  deposit: number;
  monthlyRent: number;
  includeAdjacent: boolean;
  analysis: RentListingAnalysisResponse | null;
  loading: boolean;
  error: string;
  onAddressChange: (value: string) => void;
  onAreaM2Change: (value: number) => void;
  onListingTypeChange: (value: RentListingType) => void;
  onDepositChange: (value: number) => void;
  onMonthlyRentChange: (value: number) => void;
  onIncludeAdjacentChange: (value: boolean) => void;
  onAnalyze: () => void;
}) {
  return (
    <div className="grid gap-4">
      <section className="grid gap-3">
        <p className="m-0 text-[12px] leading-5 text-text-muted">
          입력한 매물을 같은 법정동의 최근 실거래와 비교합니다. 환산월세는 분석 결과에서 함께 표시됩니다.
        </p>
        <label className="grid gap-1 text-[12px] font-bold text-text-muted">
          매물 주소
          <input
            value={address}
            onChange={(event) => onAddressChange(event.target.value)}
            className="h-10 rounded-[9px] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text outline-none focus:border-primary"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[12px] font-bold text-text-muted">
            주거 유형
            <select
              value={listingType}
              onChange={(event) => onListingTypeChange(event.target.value as RentListingType)}
              className="h-10 rounded-[9px] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text outline-none focus:border-primary"
            >
              <option value="apartment">아파트</option>
              <option value="officetel">오피스텔</option>
              <option value="villa_house">빌라/주택</option>
            </select>
          </label>
          <NumberField label="전용면적 m²" value={areaM2} onChange={onAreaM2Change} step={1} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <NumberField label="보증금 만원" value={deposit} onChange={onDepositChange} step={100} />
          <NumberField label="월세 만원" value={monthlyRent} onChange={onMonthlyRentChange} step={5} />
        </div>
        <label className="flex items-center gap-2 rounded-[9px] bg-surface-alt px-3 py-2 text-[12px] font-semibold text-text-muted">
          <input
            type="checkbox"
            checked={includeAdjacent}
            onChange={(event) => onIncludeAdjacentChange(event.target.checked)}
            className="h-[15px] w-[15px] accent-primary"
          />
          인근 법정동까지 비교 표본 넓히기
        </label>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={loading}
          className="h-10 rounded-[10px] bg-primary text-[13px] font-bold text-surface transition hover:bg-primary-hover disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? '분석 중...' : '실거래 기반 가격 분석'}
        </button>
        {error ? <p className="m-0 rounded-[9px] border border-danger/25 bg-danger-soft px-3 py-2 text-[12px] font-semibold text-danger">{error}</p> : null}
      </section>
      {analysis ? <ListingAnalysisResult analysis={analysis} /> : null}
    </div>
  );
}

function NumberField({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (value: number) => void; step?: number }) {
  return (
    <label className="grid gap-1 text-[12px] font-bold text-text-muted">
      {label}
      <input
        type="number"
        min={0}
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(event) => onChange(Number(event.target.value || 0))}
        className="h-10 rounded-[9px] border border-border bg-surface-alt px-3 text-[13px] font-semibold text-text outline-none focus:border-primary"
      />
    </label>
  );
}

function ListingAnalysisResult({ analysis }: { analysis: RentListingAnalysisResponse }) {
  const toneClass = analysis.verdict.tone === 'bad'
    ? 'border-danger text-danger'
    : analysis.verdict.tone === 'good'
      ? 'border-success text-success'
      : 'border-[var(--color-heatmap-4)] text-[var(--color-heatmap-5)]';
  const delta = analysis.stats.delta_to_median_pct;
  return (
    <section className="grid gap-3 border-t border-border pt-4">
      <div className={`border-l-4 py-1 pl-3 ${toneClass}`}>
        <span className="block text-[12px] font-bold opacity-80">분석 결과</span>
        <strong className="mt-1 block text-[26px] leading-none">{analysis.verdict.label}</strong>
        <p className="m-0 mt-2 text-[13px] leading-6">{analysis.verdict.summary}</p>
      </div>
      <div className="grid grid-cols-3 gap-2 text-[12px] text-text-muted">
        <InfoRow label="환산월세" value={`${analysis.input.converted_monthly_rent}만원`} />
        <InfoRow label="m²당 입력가" value={`${analysis.input.rent_per_area.toFixed(3)}만원`} />
        <InfoRow label="기준 중위값" value={analysis.stats.median === null ? '표본 없음' : `${analysis.stats.median.toFixed(3)}만원`} />
        <InfoRow label="분위 위치" value={analysis.stats.weighted_percentile === null ? '판단 어려움' : `상위 ${Math.max(0, 100 - analysis.stats.weighted_percentile).toFixed(1)}%`} />
        <InfoRow label="중위값 대비" value={delta === null ? '비교 불가' : `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}%`} />
        <InfoRow label="비교 표본" value={`${analysis.comparison.sample_count}건`} />
      </div>
      <div className="rounded-[9px] bg-surface-alt px-3 py-2 text-[12px] leading-5 text-text-muted">
        {analysis.region.name} · {analysis.comparison.scope} · {analysis.comparison.housing_type_label} · {analysis.basis.period}
      </div>
      <p className="m-0 text-[11px] leading-5 text-text-subtle">{analysis.disclaimer}</p>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-[9px] bg-surface-alt px-3 py-2">
      <span className="block truncate text-[10px] font-bold text-text-subtle">{label}</span>
      <b className="mt-0.5 block truncate text-[13px] text-text">{value}</b>
    </div>
  );
}

export function RealEstateLinks() {
  return (
    <div className="grid gap-4">
      <LinkGroup title="매물·시세 확인" caption="가격 비교" links={[
        { logoSrc: govSymbolLogo, logoAlt: '정부 상징', title: '국토교통부 실거래가', description: '주변 시세와 최근 거래 확인', href: 'https://rt.molit.go.kr/' },
        { logoSrc: naverPayLogo, logoAlt: '네이버페이 로고', title: '네이버페이 부동산', description: '지역 기반 매물과 동네 정보 확인', href: 'https://fin.land.naver.com/home', fillFrame: true },
        { logoSrc: kbLandLogo, logoAlt: 'KB부동산 로고', title: 'KB부동산', description: '시세와 가격 흐름 참고', href: 'https://kbland.kr/' },
        { logoSrc: rebLogo, logoAlt: '한국부동산원 로고', title: '한국부동산원', description: '공식 통계와 부동산테크', href: 'https://www.reb.or.kr/' },
        { logoSrc: zigbangLogo, logoAlt: '직방 로고', title: '직방', description: '외부 매물 탐색', href: 'https://www.zigbang.com/', fillFrame: true },
        { logoSrc: dabangLogo, logoAlt: '다방 로고', title: '다방', description: '외부 매물 탐색', href: 'https://www.dabangapp.com/' },
      ]} />
      <LinkGroup title="등기·서류 확인" caption="권리관계" links={[
        { logoSrc: courtLogo, logoAlt: '법원 로고', title: '인터넷등기소', description: '등기부등본 권리관계 확인', href: 'https://www.iros.go.kr/' },
        { logoSrc: govSymbolLogo, logoAlt: '정부 상징', title: '정부24', description: '건축물대장 등 민원 확인', href: 'https://www.gov.kr/' },
        { logoSrc: seoulLogo, logoAlt: '서울시 로고', title: '서울부동산정보광장', description: '서울 부동산 정보와 중개업소 확인', href: 'https://land.seoul.go.kr/land/' },
      ]} />
      <LinkGroup title="보증·상담" caption="위험 점검" links={[
        { logoSrc: hugLogo, logoAlt: 'HUG 로고', title: 'HUG 주택도시보증공사', description: '보증 가입 가능 여부와 안내', href: 'https://www.khug.or.kr/' },
        { logoSrc: seoulLogo, logoAlt: '서울시 로고', title: '서울주거포털', description: '전월세 종합지원센터 안내', href: 'https://housing.seoul.go.kr/site/main/content/sh05_070200' },
        { logoSrc: govSymbolLogo, logoAlt: '정부 상징', title: '국토교통부 안전전세', description: '전세사기 예방 체크리스트', href: 'https://www.molit.go.kr/2023safehome/main.jsp' },
      ]} />
    </div>
  );
}

function LinkGroup({
  title,
  caption,
  links,
}: {
  title: string;
  caption: string;
  links: RealEstateLink[];
}) {
  return (
    <section className="grid gap-2">
      <h3 className="m-0 flex items-center justify-between text-[15px] font-bold text-primary">
        {title}
        <span className="text-[11px] font-semibold text-text-muted">{caption}</span>
      </h3>
      <div className="grid gap-2 md:grid-cols-2">
        {links.map(({ logoSrc, logoAlt, title: titleText, description, href, fillFrame }) => (
          <a key={href} href={href} target="_blank" rel="noreferrer" className="grid min-h-16 grid-cols-[42px_1fr_auto] items-center gap-3 rounded-card border border-border bg-surface p-3 text-text no-underline transition hover:border-primary hover:bg-primary-soft">
            <span className={`inline-flex h-[42px] w-[42px] items-center justify-center overflow-hidden rounded-[10px] border border-border/70 bg-surface-alt shadow-sm ${fillFrame ? 'p-0' : 'p-1'}`}>
              <img src={logoSrc} alt={logoAlt} className={`block h-full w-full ${fillFrame ? 'object-cover' : 'object-contain'}`} />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[14px] font-bold">{titleText}</span>
              <span className="mt-0.5 block truncate text-[12px] text-text-muted">{description}</span>
            </span>
            <span aria-hidden="true" className="text-text-muted">↗</span>
          </a>
        ))}
      </div>
    </section>
  );
}
