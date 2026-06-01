import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import courtLogo from '@/assets/logos/real-estate/court.png';
import dabangLogo from '@/assets/logos/real-estate/dabang.png';
import govSymbolLogo from '@/assets/logos/real-estate/gov-symbol.png';
import hugLogo from '@/assets/logos/real-estate/hug.png';
import kbLandLogo from '@/assets/logos/real-estate/kb-land.png';
import naverPayLogo from '@/assets/logos/real-estate/naver-pay.png';
import rebLogo from '@/assets/logos/real-estate/reb.png';
import seoulLogo from '@/assets/logos/real-estate/seoul.png';
import zigbangLogo from '@/assets/logos/real-estate/zigbang.png';
import { analyzeRentListing, getRentConversionRate } from '@/lib/api';
import { MONTHLY_CONVERSION_RATE } from '@/lib/rent';
import type { RentListingAnalysisResponse, RentListingType } from '@/types/api';

type RealEstateHelperTab = 'checklist' | 'calculator' | 'analysis' | 'links';
type RealEstateLink = {
  logoSrc: string;
  logoAlt: string;
  title: string;
  description: string;
  href: string;
  fillFrame?: boolean;
};

const DEFAULT_ANNUAL_CONVERSION_RATE = Number((MONTHLY_CONVERSION_RATE * 12 * 100).toFixed(3));

function convertByAnnualRate(deposit: number, monthlyRent: number, annualRate: number) {
  const safeDeposit = Math.max(0, Number.isFinite(deposit) ? deposit : 0);
  const safeMonthly = Math.max(0, Number.isFinite(monthlyRent) ? monthlyRent : 0);
  const safeRate = Math.max(0, Number.isFinite(annualRate) ? annualRate : DEFAULT_ANNUAL_CONVERSION_RATE);
  return Math.floor(safeMonthly + (safeDeposit * (safeRate / 100)) / 12);
}

export default function RealEstateHelperPanel({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  const [activeTab, setActiveTab] = useState<RealEstateHelperTab>('checklist');
  const [deposit, setDeposit] = useState(5000);
  const [monthlyRent, setMonthlyRent] = useState(60);
  const [annualRate, setAnnualRate] = useState(DEFAULT_ANNUAL_CONVERSION_RATE);
  const [listingAddress, setListingAddress] = useState('서울특별시 관악구 신림동');
  const [listingDeposit, setListingDeposit] = useState(1000);
  const [listingMonthly, setListingMonthly] = useState(65);
  const [listingAreaM2, setListingAreaM2] = useState(20);
  const [listingType, setListingType] = useState<RentListingType>('villa_house');
  const [listingIncludeAdjacent, setListingIncludeAdjacent] = useState(false);
  const [listingAnalysis, setListingAnalysis] = useState<RentListingAnalysisResponse | null>(null);
  const [listingAnalysisError, setListingAnalysisError] = useState('');
  const [listingAnalysisLoading, setListingAnalysisLoading] = useState(false);
  const convertedRent = convertByAnnualRate(deposit, monthlyRent, annualRate);
  const listingConvertedRent = convertByAnnualRate(listingDeposit, listingMonthly, annualRate);
  const conversionRateQuery = useQuery({
    queryKey: ['rent-deals', 'conversion-rate'],
    queryFn: getRentConversionRate,
    staleTime: 60 * 60 * 1000,
    enabled: open,
  });

  useEffect(() => {
    if (typeof conversionRateQuery.data?.annual_rate !== 'number') return;
    setAnnualRate(Number(conversionRateQuery.data.annual_rate.toFixed(3)));
  }, [conversionRateQuery.data?.annual_rate]);

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
    <div className="pointer-events-none relative w-[132px]">
      <div className="pointer-events-auto grid w-full gap-2">
        <button
          type="button"
          onClick={onToggle}
          className={`flex h-10 w-full items-center justify-center gap-1.5 rounded-[var(--map-control-radius)] border px-2 text-[12px] font-semibold tracking-normal shadow-lg backdrop-blur transition ${
            open
              ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
              : 'border-[var(--color-heatmap-2)]/50 bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
          }`}
          aria-expanded={open}
        >
          <span className="text-[12px] leading-none" aria-hidden="true">✓</span>
          <span className="truncate">부동산 도우미</span>
        </button>

        <div className="group relative z-[300] w-max">
          <button type="button" aria-label="부동산 지도 안내" className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border/80 bg-surface/70 text-[11px] font-bold text-text-subtle shadow-sm backdrop-blur focus:outline-none">i</button>
          <div className="pointer-events-none absolute left-[calc(100%+8px)] top-0 z-[1000] hidden w-[340px] rounded-card border border-[var(--color-heatmap-2)] bg-[var(--surface-overlay-bg)] p-3 text-[12px] leading-5 text-text shadow-xl backdrop-blur-md group-hover:block">
            <p className="m-0">지도 핀은 과거 실거래 캐시를 프론트에서 필터링해 묶은 요약입니다. 가격은 그룹의 대표 환산월세, 건수는 필터를 통과한 거래 수입니다.</p>
            <p className="m-0 mt-1">환산월세는 한국부동산원 전월세전환율 최근 서울 평균으로 계산합니다.</p>
            <p className="m-0 mt-2">{"과거 원천 데이터 일부는 연립과 다세대가 연립다세대로 통합되어 함께 반영될 수 있습니다. 단독·다가구는 원천 데이터 특성상 개별 주소/좌표가 없어 지도 핀으로 표시되지 않고 법정동 요약에서만 다룹니다."}</p>
          </div>
        </div>
      </div>

      {open ? (
        <aside className="pointer-events-auto absolute left-[calc(100%+8px)] top-[-104px] z-[1200] grid max-h-[min(820px,calc(100vh-24px))] w-[500px] grid-rows-[auto_auto_1fr] overflow-hidden rounded-card border border-[var(--color-heatmap-2)]/50 bg-surface/95 text-text shadow-2xl backdrop-blur" aria-label="부동산 도우미">
          <header className="border-b border-border/70 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="m-0 text-[15px] font-bold text-text">부동산 도우미</h2>
                <p className="m-0 mt-1 text-[12px] leading-5 text-text-muted">계약 전 확인, 환산월세 계산, 실거래 기반 가격 분석, 외부 링크를 한 곳에서 봅니다.</p>
              </div>
              <button type="button" onClick={onToggle} className="h-7 w-7 rounded-[6px] bg-surface-alt text-[16px] text-text-muted hover:bg-border/60" aria-label="부동산 도우미 닫기">×</button>
            </div>
          </header>

          <div className="grid grid-cols-4 gap-1 border-b border-border/70 bg-surface-alt/80 p-2">
            {([
              ['checklist', '체크리스트'],
              ['calculator', '환산월세'],
              ['analysis', '매물 분석'],
              ['links', '외부 링크'],
            ] as Array<[RealEstateHelperTab, string]>).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`h-8 rounded-[9px] text-[12px] font-bold transition ${
                  activeTab === tab
                    ? 'bg-surface text-[var(--color-heatmap-5)] shadow-sm'
                    : 'text-text-muted hover:bg-surface/70 hover:text-text'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="overflow-y-auto p-3">
            {activeTab === 'checklist' ? <RealEstateChecklist /> : null}
            {activeTab === 'calculator' ? (
              <RealEstateCalculator
                deposit={deposit}
                monthlyRent={monthlyRent}
                annualRate={annualRate}
                convertedRent={convertedRent}
                onDepositChange={setDeposit}
                onMonthlyRentChange={setMonthlyRent}
                onAnnualRateChange={setAnnualRate}
                rateSource={conversionRateQuery.data?.source ?? '한국부동산원 전월세전환율 최근 서울 평균'}
                rateLoading={conversionRateQuery.isLoading}
              />
            ) : null}
            {activeTab === 'analysis' ? (
              <RealEstateListingAnalysis
                address={listingAddress}
                areaM2={listingAreaM2}
                listingType={listingType}
                deposit={listingDeposit}
                monthlyRent={listingMonthly}
                convertedRent={listingConvertedRent}
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
        </aside>
      ) : null}
    </div>
  );
}

function RealEstateChecklist() {
  return (
    <div className="grid gap-2">
      <ChecklistCard title="계약 전" hint="가격과 권리관계가 안전한지 먼저 거릅니다." items={[
        '실거래가, 주변 매물, KB/부동산원 시세를 비교해 가격이 과도하지 않은지 확인',
        '전세가율 확인. 전세가가 매매가의 80%를 넘으면 위험 신호로 보기',
        '등기부등본으로 소유자, 근저당, 가압류, 압류, 가처분 확인',
        '신탁등기가 있으면 신탁원부와 신탁회사 임대 동의 여부 확인',
        '건축물대장으로 위반건축물, 무허가, 근린생활시설 여부 확인',
        '임대인 국세·지방세 체납 열람 가능 여부 확인',
        'HUG 등 전세보증금 반환보증 가입 가능 여부 확인',
        '다가구/단독이면 선순위 임차인과 선순위 보증금 규모 확인',
      ]} />
      <ChecklistCard title="계약 시" hint="계약 당사자와 계약서 문구를 확인합니다." items={[
        '임대인 신분증과 등기부 소유자 일치 확인',
        '공동소유면 소유자 전원 동의 또는 계약 참여 여부 확인',
        '법인 임대인이면 법인등기, 대표자 신분, 법인 인감 확인',
        '대리인 계약이면 위임장, 인감증명서, 임대인 직접 연락 확인',
        '공인중개사 등록 상태, 정상 영업 여부, 공제증서 확인',
        '계약금·잔금 입금 계좌가 임대인 명의인지 확인',
        '잔금 다음날까지 근저당 등 권리변동 금지 특약 검토',
        '보증보험 가입 협조, 권리하자·체납 발견 시 계약 해제 특약 검토',
      ]} />
      <ChecklistCard title="잔금/입주 후" hint="잔금 전후 권리 변동과 보증 절차를 마무리합니다." items={[
        '잔금 직전 등기부등본을 다시 발급해 권리 변동 확인',
        '입주 즉시 전입신고와 확정일자 처리',
        '주택 임대차 계약 신고 대상이면 신고 여부 확인',
        '전세보증금 반환보증 가입 완료',
        '입주 후 일정 기간 뒤 등기부를 다시 확인해 추가 권리 설정 여부 확인',
      ]} />
      <p className="m-0 text-[11px] leading-5 text-text-subtle">체크 상태는 저장하지 않고 현재 화면에서만 유지됩니다.</p>
    </div>
  );
}

function ChecklistCard({ title, hint, items }: { title: string; hint: string; items: string[] }) {
  return (
    <section className="rounded-card border border-border bg-surface p-3">
      <strong className="block text-[13px] text-[var(--color-heatmap-5)]">{title}</strong>
      <span className="mt-1 block text-[11px] leading-4 text-text-muted">{hint}</span>
      <ul className="m-0 mt-2 grid gap-1.5 p-0">
        {items.map((item, index) => {
          const id = `realestate-check-${title}-${index}`;
          return (
            <li key={item} className="grid grid-cols-[18px_1fr] items-start gap-2 text-[12px] leading-5 text-text-muted">
              <input id={id} type="checkbox" className="peer mt-1 h-[15px] w-[15px] accent-[var(--color-heatmap-5)]" />
              <label htmlFor={id} className="cursor-pointer peer-checked:text-text-subtle">{item}</label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function RealEstateCalculator({
  deposit,
  monthlyRent,
  annualRate,
  convertedRent,
  rateSource,
  rateLoading,
  onDepositChange,
  onMonthlyRentChange,
  onAnnualRateChange,
}: {
  deposit: number;
  monthlyRent: number;
  annualRate: number;
  convertedRent: number;
  rateSource: string;
  rateLoading: boolean;
  onDepositChange: (value: number) => void;
  onMonthlyRentChange: (value: number) => void;
  onAnnualRateChange: (value: number) => void;
}) {
  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 gap-2">
        <NumberField label="보증금" value={deposit} onChange={onDepositChange} step={100} />
        <NumberField label="월세" value={monthlyRent} onChange={onMonthlyRentChange} step={5} />
      </div>
      <div className="grid grid-cols-[1fr_auto] items-end gap-2">
        <NumberField label="전환율" value={annualRate} onChange={onAnnualRateChange} step={0.05} />
        <span className="pb-2 text-[11px] font-semibold text-text-muted">연 %</span>
      </div>
      <div className="rounded-card border border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] p-3">
        <span className="block text-[11px] font-bold text-text-muted">계산된 환산월세</span>
        <div className="mt-1 flex items-baseline gap-2 text-[var(--color-heatmap-5)]">
          <strong className="text-[34px] leading-none">{convertedRent}</strong>
          <span className="text-[12px] font-bold">월세 기준</span>
        </div>
        <p className="m-0 mt-1 text-[11px] leading-5 text-text-muted">보증금을 월세로 환산한 값입니다. 결과는 만원 단위로 절삭합니다.</p>
      </div>
      <p className="m-0 text-[11px] leading-5 text-text-muted">기본 전환율은 {rateLoading ? '불러오는 중입니다' : rateSource + ' 기준입니다'}. 사용자가 직접 바꿔서 계산할 수 있습니다.</p>
    </div>
  );
}

function NumberField({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (value: number) => void; step?: number }) {
  return (
    <label className="grid gap-1 text-[11px] font-bold text-text-muted">
      {label}
      <input
        type="number"
        min={0}
        step={step}
        value={Number.isFinite(value) ? value : 0}
        onChange={(event) => onChange(Number(event.target.value || 0))}
        className="h-9 rounded-[9px] border border-border bg-surface px-2 text-[12px] font-semibold text-text outline-none focus:border-[var(--color-heatmap-2)]"
      />
    </label>
  );
}

function RealEstateListingAnalysis({
  address,
  areaM2,
  listingType,
  deposit,
  monthlyRent,
  convertedRent,
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
  convertedRent: number;
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
    <div className="grid gap-3">
      <div className="grid gap-2 rounded-card border border-border bg-surface p-3">
        <label className="grid gap-1 text-[11px] font-bold text-text-muted">
          매물 주소
          <input
            value={address}
            onChange={(event) => onAddressChange(event.target.value)}
            className="h-9 rounded-[9px] border border-border bg-surface px-2 text-[12px] font-semibold text-text outline-none focus:border-[var(--color-heatmap-2)]"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[11px] font-bold text-text-muted">
            주거 유형
            <select
              value={listingType}
              onChange={(event) => onListingTypeChange(event.target.value as RentListingType)}
              className="h-9 rounded-[9px] border border-border bg-surface px-2 text-[12px] font-semibold text-text outline-none focus:border-[var(--color-heatmap-2)]"
            >
              <option value="apartment">아파트</option>
              <option value="officetel">오피스텔</option>
              <option value="villa_house">빌라·주택</option>
            </select>
          </label>
          <NumberField label="전용면적㎡" value={areaM2} onChange={onAreaM2Change} step={1} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <NumberField label="보증금" value={deposit} onChange={onDepositChange} step={100} />
          <NumberField label="월세" value={monthlyRent} onChange={onMonthlyRentChange} step={5} />
        </div>
        <label className="flex items-center gap-2 rounded-[9px] bg-surface-alt px-2.5 py-2 text-[12px] font-semibold text-text-muted">
          <input
            type="checkbox"
            checked={includeAdjacent}
            onChange={(event) => onIncludeAdjacentChange(event.target.checked)}
            className="h-[15px] w-[15px] accent-[var(--color-heatmap-5)]"
          />
          인근 법정동까지 표본 넓히기
        </label>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={loading}
          className="h-9 rounded-[10px] bg-[var(--color-heatmap-5)] text-[12px] font-bold text-white transition disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? '분석 중...' : '실거래 기반 가격 분석'}
        </button>
        {error ? <p className="m-0 rounded-[9px] bg-red-50 px-2.5 py-2 text-[12px] font-semibold text-red-700">{error}</p> : null}
      </div>
      <div className="grid gap-2 rounded-card border border-border bg-surface p-3">
        <div className="rounded-card border border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] p-3">
          <span className="block text-[11px] font-bold text-text-muted">입력 매물 환산월세</span>
          <strong className="mt-1 block text-[34px] leading-none text-[var(--color-heatmap-5)]">{convertedRent}</strong>
        </div>
        <ul className="m-0 grid gap-1.5 p-0 text-[12px] text-text-muted">
          <li className="flex justify-between gap-3 rounded-[9px] bg-surface-alt px-2.5 py-2"><span>비교 데이터</span><b className="text-text">국토교통부 실거래가</b></li>
          <li className="flex justify-between gap-3 rounded-[9px] bg-surface-alt px-2.5 py-2"><span>비교 방식</span><b className="text-text">{includeAdjacent ? '인근 법정동 포함' : '해당 법정동'}</b></li>
        </ul>
      </div>
      {analysis ? <ListingAnalysisResult analysis={analysis} /> : null}
      <p className="m-0 text-[11px] leading-5 text-text-muted">최근 24개월 실거래에 시간 감쇠 가중치를 적용합니다. 결과는 참고용이며 실제 계약 판단은 관리비와 매물 상태를 함께 확인해야 합니다.</p>
    </div>
  );
}

function ListingAnalysisResult({ analysis }: { analysis: RentListingAnalysisResponse }) {
  const toneClass = analysis.verdict.tone === 'bad'
    ? 'border-red-200 bg-red-50 text-red-700'
    : analysis.verdict.tone === 'good'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]';
  const delta = analysis.stats.delta_to_median_pct;
  return (
    <div className="grid gap-2 rounded-card border border-border bg-surface p-3">
      <div className={`rounded-card border p-3 ${toneClass}`}>
        <span className="block text-[11px] font-bold opacity-80">분석 결과</span>
        <strong className="mt-1 block text-[22px] leading-none">{analysis.verdict.label}</strong>
        <p className="m-0 mt-2 text-[12px] leading-5">{analysis.verdict.summary}</p>
      </div>
      <div className="grid grid-cols-2 gap-1.5 text-[12px] text-text-muted">
        <InfoRow label="입력 ㎡당" value={`${analysis.input.rent_per_area.toFixed(3)}만원`} />
        <InfoRow label="기준 중위값" value={analysis.stats.median === null ? '표본 없음' : `${analysis.stats.median.toFixed(3)}만원`} />
        <InfoRow label="분위 위치" value={analysis.stats.weighted_percentile === null ? '판단 어려움' : `상위 ${Math.max(0, 100 - analysis.stats.weighted_percentile).toFixed(1)}%`} />
        <InfoRow label="중위값 대비" value={delta === null ? '비교 불가' : `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}%`} />
        <InfoRow label="비교 표본" value={`${analysis.comparison.sample_count}건`} />
        <InfoRow label="신뢰도" value={analysis.comparison.confidence_label} />
      </div>
      <div className="rounded-[9px] bg-surface-alt px-2.5 py-2 text-[11px] leading-5 text-text-muted">
        {analysis.region.name} · {analysis.comparison.scope} · {analysis.comparison.housing_type_label} · {analysis.basis.period} · 시간 감쇠 적용
      </div>
      <p className="m-0 text-[11px] leading-5 text-text-subtle">{analysis.disclaimer}</p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-[9px] bg-surface-alt px-2.5 py-2">
      <span className="block truncate text-[10px] font-bold text-text-subtle">{label}</span>
      <b className="mt-0.5 block truncate text-[12px] text-text">{value}</b>
    </div>
  );
}

function RealEstateLinks() {
  return (
    <div className="grid gap-3">
      <LinkGroup title="매물·시세 확인" caption="가격 비교" links={[
        { logoSrc: govSymbolLogo, logoAlt: '정부상징', title: '국토교통부 실거래가', description: '주변 시세와 최근 거래 확인', href: 'https://rt.molit.go.kr/' },
        { logoSrc: naverPayLogo, logoAlt: '네이버페이 로고', title: '네이버페이 부동산', description: '지도 기반 매물과 지역 정보 확인', href: 'https://fin.land.naver.com/home', fillFrame: true },
        { logoSrc: kbLandLogo, logoAlt: 'KB부동산 로고', title: 'KB부동산', description: '시세, 단지, 지역 가격 흐름 참고', href: 'https://kbland.kr/' },
        { logoSrc: rebLogo, logoAlt: '한국부동산원 로고', title: '한국부동산원', description: '부동산테크, R-ONE 등 공식 통계 연결', href: 'https://www.reb.or.kr/' },
        { logoSrc: zigbangLogo, logoAlt: '직방 로고', title: '직방', description: '외부 매물 탐색', href: 'https://www.zigbang.com/', fillFrame: true },
        { logoSrc: dabangLogo, logoAlt: '다방 로고', title: '다방', description: '외부 매물 탐색', href: 'https://www.dabangapp.com/' },
      ]} />
      <LinkGroup title="등기·서류 확인" caption="권리관계" links={[
        { logoSrc: courtLogo, logoAlt: '법원 로고', title: '인터넷등기소', description: '등기부등본 권리관계 확인', href: 'https://www.iros.go.kr/' },
        { logoSrc: govSymbolLogo, logoAlt: '정부상징', title: '정부24', description: '건축물대장, 주민등록 등 민원 확인', href: 'https://www.gov.kr/' },
        { logoSrc: seoulLogo, logoAlt: '서울시 로고', title: '서울부동산정보광장', description: '서울 부동산 정보와 중개업소 확인', href: 'https://land.seoul.go.kr/land/' },
      ]} />
      <LinkGroup title="보증·상담" caption="피해 예방" links={[
        { logoSrc: hugLogo, logoAlt: 'HUG 로고', title: 'HUG 주택도시보증공사', description: '보증 가능 여부와 임대인 조회', href: 'https://www.khug.or.kr/' },
        { logoSrc: seoulLogo, logoAlt: '서울시 로고', title: '서울주거포털 전세사기 예방', description: '전월세종합지원센터와 예방 자료', href: 'https://housing.seoul.go.kr/site/main/content/sh05_070200' },
        { logoSrc: govSymbolLogo, logoAlt: '정부상징', title: '국토교통부 안전한 집', description: '전세사기 예방 체크리스트와 셀프 테스트', href: 'https://www.molit.go.kr/2023safehome/main.jsp' },
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
    <section className="grid gap-1.5">
      <h3 className="m-0 flex items-center justify-between text-[12px] font-bold text-[var(--color-heatmap-5)]">
        {title}
        <span className="text-[10px] font-semibold text-text-muted">{caption}</span>
      </h3>
      {links.map(({ logoSrc, logoAlt, title: titleText, description, href, fillFrame }) => (
        <a key={href} href={href} target="_blank" rel="noreferrer" className="grid min-h-14 grid-cols-[34px_1fr_auto] items-center gap-2 rounded-card border border-border bg-surface p-2.5 text-text no-underline transition hover:border-[var(--color-heatmap-2)] hover:bg-[var(--color-heatmap-1)]">
          <span className={`inline-flex h-[34px] w-[34px] items-center justify-center overflow-hidden rounded-[10px] border border-border/70 bg-surface-alt shadow-sm ${fillFrame ? 'p-0' : 'p-0.5'}`}>
            <img src={logoSrc} alt={logoAlt} className={`block h-full w-full ${fillFrame ? 'object-cover' : 'object-contain'}`} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[13px] font-bold">{titleText}</span>
            <span className="mt-0.5 block truncate text-[11px] text-text-muted">{description}</span>
          </span>
          <span aria-hidden="true" className="text-text-muted">↗</span>
        </a>
      ))}
    </section>
  );
}
