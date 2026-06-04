import { useEffect, useState } from 'react';

import { analyzeRentListing } from '@/features/common/lib/api';
import type { RentListingAnalysisResponse, RentListingType } from '@/features/common/types/api';
import {
  RealEstateChecklist,
  RealEstateLinks,
  RealEstateListingAnalysis,
  type RealEstateHelperTab,
} from '@/features/real-estate/routes/RealEstatePage';

interface RealEstateHelperPanelProps {
  isOpen: boolean;
  initialTab: RealEstateHelperTab;
  address: string;
  onClose: () => void;
}

const PANEL_META: Record<RealEstateHelperTab, { title: string; subtitle: string }> = {
  checklist: {
    title: '부동산 계약 체크리스트',
    subtitle: '계약 전·계약 당일·입주 후 확인 항목',
  },
  analysis: {
    title: '실거래 기반 매물 분석',
    subtitle: '보증금·월세·면적 기준 비교',
  },
  links: {
    title: '부동산 외부 링크 모음',
    subtitle: '시세·등기·보증·공공 정보',
  },
};

export default function RealEstateHelperPanel({
  isOpen,
  initialTab,
  address,
  onClose,
}: RealEstateHelperPanelProps) {
  const [activeTab, setActiveTab] = useState<RealEstateHelperTab>(initialTab);
  const [listingAddress, setListingAddress] = useState(address || '서울특별시 관악구 신림동');
  const [listingDeposit, setListingDeposit] = useState(1000);
  const [listingMonthly, setListingMonthly] = useState(65);
  const [listingAreaM2, setListingAreaM2] = useState(20);
  const [listingType, setListingType] = useState<RentListingType>('villa_house');
  const [listingIncludeAdjacent, setListingIncludeAdjacent] = useState(false);
  const [listingAnalysis, setListingAnalysis] = useState<RentListingAnalysisResponse | null>(null);
  const [listingAnalysisError, setListingAnalysisError] = useState('');
  const [listingAnalysisLoading, setListingAnalysisLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab(initialTab);
    if (address) setListingAddress(address);
  }, [address, initialTab, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

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

  if (!isOpen) return null;

  const meta = PANEL_META[activeTab];
  const subtitle = activeTab === 'analysis' && listingAddress ? listingAddress : meta.subtitle;

  return (
    <aside
      className="flex max-h-[calc(100vh-40px)] w-[560px] max-w-[calc(100vw-370px)] flex-col overflow-hidden rounded-card border border-border bg-surface/95 text-text shadow-floating backdrop-blur"
      aria-label={meta.title}
    >
      <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
        <div className="min-w-0">
          <h2 className="m-0 text-[17px] font-bold">{meta.title}</h2>
          <p className="m-0 mt-1 truncate text-[12px] font-semibold text-text-muted">
            {subtitle}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="h-8 w-8 shrink-0 rounded-[8px] bg-surface-alt text-[18px] font-bold leading-none text-text-muted transition hover:text-text"
          aria-label={`${meta.title} 닫기`}
        >
          ×
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
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
    </aside>
  );
}
