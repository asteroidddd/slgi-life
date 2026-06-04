import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

import dabangLogo from '@/assets/logos/real-estate/dabang.png';
import naverPayLogo from '@/assets/logos/real-estate/naver-pay.png';
import zigbangLogo from '@/assets/logos/real-estate/zigbang.png';
import {
  buildRealEstateListingLinks,
  type ListingHouseType,
} from '@/features/real-estate/lib/listingLinks';
import RealEstateHelperPanel from '@/features/real-estate/components/RealEstateHelperPanel';
import type { RealEstateHelperTab } from '@/features/real-estate/routes/RealEstatePage';

interface ListingPanelRegion {
  gu: string;
  name: string;
  lat: number;
  lng: number;
}

interface ListingMapView {
  lat: number;
  lng: number;
  zoom: number;
}

interface ListingLinkPanelProps {
  region: ListingPanelRegion | null;
  zoom: number;
  mapView: ListingMapView | null;
}

const PANEL_LEFT_STYLE = {
  left: 'max(var(--dashboard-page-padding), calc((100vw - var(--dashboard-max-width)) / 2 + var(--dashboard-page-padding)))',
  top: 'var(--dashboard-page-padding)',
} satisfies CSSProperties;

function readDashboardCardLeft() {
  if (typeof document === 'undefined') return null;
  const card = document.querySelector<HTMLElement>('[data-dashboard-main-card="true"]');
  const left = card?.getBoundingClientRect().left;
  return typeof left === 'number' && Number.isFinite(left) ? Math.round(left) : null;
}

const HOUSE_TYPES: Array<{ key: ListingHouseType; label: string }> = [
  { key: 'one-room', label: '원룸' },
  { key: 'villa', label: '빌라' },
  { key: 'apartment', label: '아파트' },
  { key: 'officetel', label: '오피스텔' },
];

const LOGOS = {
  naver: { src: naverPayLogo, alt: '네이버페이 부동산' },
  zigbang: { src: zigbangLogo, alt: '직방' },
  dabang: { src: dabangLogo, alt: '다방' },
};

const HELPER_ACTIONS: Array<{
  key: RealEstateHelperTab;
  label: string;
  description: string;
}> = [
  { key: 'checklist', label: '부동산 계약 체크리스트', description: '계약 전 확인 항목' },
  { key: 'analysis', label: '실거래 기반 매물 분석', description: '보증금·월세 비교' },
  { key: 'links', label: '부동산 외부 링크 모음', description: '시세·등기·보증 사이트' },
];

function hasValidRegion(region: ListingPanelRegion | null): region is ListingPanelRegion {
  return Boolean(region)
    && Number.isFinite(region?.lat)
    && Number.isFinite(region?.lng)
    && !(region?.lat === 0 && region?.lng === 0);
}

export default function ListingLinkPanel({ region, zoom, mapView }: ListingLinkPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [houseType, setHouseType] = useState<ListingHouseType>('one-room');
  const [helperTab, setHelperTab] = useState<RealEstateHelperTab | null>(null);
  const [helperLeft, setHelperLeft] = useState<number | null>(() => readDashboardCardLeft());
  const validRegion = hasValidRegion(region);
  const helperAddress = region ? `서울특별시 ${region.gu} ${region.name}` : '';

  const links = useMemo(() => {
    if (!hasValidRegion(region)) return [];
    return buildRealEstateListingLinks({
      dongName: region.name,
      lat: mapView?.lat ?? region.lat,
      lng: mapView?.lng ?? region.lng,
      zoom: mapView?.zoom ?? zoom,
      houseType,
    });
  }, [houseType, mapView?.lat, mapView?.lng, mapView?.zoom, region, zoom]);

  useEffect(() => {
    if (helperTab === null) return;
    let frame = 0;
    const updateLeft = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        setHelperLeft(readDashboardCardLeft());
      });
    };
    updateLeft();
    window.addEventListener('resize', updateLeft);
    window.visualViewport?.addEventListener('resize', updateLeft);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener('resize', updateLeft);
      window.visualViewport?.removeEventListener('resize', updateLeft);
    };
  }, [helperTab]);

  if (!region) return null;

  const helperPanelStyle = helperLeft === null
    ? PANEL_LEFT_STYLE
    : ({ left: `${helperLeft}px`, top: 'var(--dashboard-page-padding)' } satisfies CSSProperties);

  return (
    <>
      <aside
        className={`fixed left-6 top-[126px] z-[1420] flex max-h-[calc(100vh-150px)] ${collapsed ? 'w-[190px]' : 'w-[292px]'} flex-col overflow-hidden rounded-card border border-border bg-surface/95 text-text shadow-floating backdrop-blur`}
        aria-label="실제 매물 보기"
      >
        <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h2 className="m-0 text-[15px] font-bold">{collapsed ? '실제 매물' : '실제 매물 보기'}</h2>
            <p className="m-0 mt-1 truncate text-[11px] font-semibold text-text-muted">
              {region.gu} {region.name}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            className="h-7 shrink-0 rounded-[6px] bg-surface-alt px-2 text-[11px] font-bold text-text-muted transition hover:text-text"
            aria-label={collapsed ? '실제 매물 보기 펼치기' : '실제 매물 보기 접기'}
            aria-expanded={!collapsed}
          >
            {collapsed ? '펼치기' : '접기'}
          </button>
        </header>

        {collapsed ? null : (
          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            <div className="grid gap-3">
              <div className="grid grid-cols-4 gap-1 rounded-[10px] border border-border bg-surface-alt p-1" role="group" aria-label="주택유형 선택">
                {HOUSE_TYPES.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setHouseType(item.key)}
                    className={`h-8 rounded-[8px] text-[11px] font-bold transition ${
                      houseType === item.key
                        ? 'bg-surface text-primary shadow-sm'
                        : 'text-text-muted hover:bg-surface/70 hover:text-text'
                    }`}
                    aria-pressed={houseType === item.key}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {validRegion ? (
                <nav className="grid grid-cols-3 gap-2" aria-label="외부 매물 사이트">
                  {links.map((link) => {
                    const logo = LOGOS[link.key];
                    return (
                      <a
                        key={link.key}
                        href={link.href}
                        target="_blank"
                        rel="noreferrer"
                        className="flex min-h-[76px] flex-col items-center justify-center gap-2 rounded-[10px] bg-transparent px-1 py-2 text-text no-underline transition hover:bg-primary-soft/60"
                        aria-label={`${link.title}에서 ${region.name} 매물 보기`}
                        title={link.title}
                      >
                        <span className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-[10px]">
                          <img src={logo.src} alt={logo.alt} className="block h-full w-full object-contain" />
                        </span>
                        <span className="max-w-full whitespace-normal break-keep text-center text-[11px] font-bold leading-tight text-text-muted">
                          {link.title}
                        </span>
                      </a>
                    );
                  })}
                </nav>
              ) : (
                <p className="m-0 rounded-[10px] border border-border bg-surface-alt px-3 py-3 text-[12px] leading-5 text-text-muted">
                  이 동네는 중심 좌표가 없어 외부 매물 링크를 만들 수 없습니다.
                </p>
              )}

              <div className="grid gap-2 border-t border-border pt-3" aria-label="부동산 보조 기능">
                {HELPER_ACTIONS.map((action) => (
                  <button
                    key={action.key}
                    type="button"
                    onClick={() => setHelperTab((prev) => (prev === action.key ? null : action.key))}
                    className={`grid gap-0.5 rounded-[10px] border px-3 py-2 text-left transition ${
                      helperTab === action.key
                        ? 'border-primary bg-primary-soft text-primary'
                        : 'border-border bg-surface text-text hover:border-primary hover:text-primary'
                    }`}
                  >
                    <span className="text-[12px] font-bold">{action.label}</span>
                    <span className="text-[11px] font-semibold text-text-muted">{action.description}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </aside>

      {helperTab !== null ? (
        <div
          className="fixed z-[1420] max-w-[calc(100vw-48px)]"
          style={helperPanelStyle}
        >
          <RealEstateHelperPanel
            isOpen
            initialTab={helperTab}
            address={helperAddress}
            onClose={() => setHelperTab(null)}
          />
        </div>
      ) : null}
    </>
  );
}
