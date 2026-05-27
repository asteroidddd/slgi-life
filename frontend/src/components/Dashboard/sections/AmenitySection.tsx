// Dashboard AmenitySection -- SPEC 4.4 Section B (편의시설).
//
// Widgets:
//   1. Category table (8 categories: count, density, TOP X%, sufficiency badge)
//   2. Large parks list (TOP N by area) — AdongParksResponse
//   3. Library placeholder (data not available)
//
// Data: AdongDetail.amenities + AdongScore[] (for percentile) + AdongParksResponse

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import { CATEGORY_COLORS } from '@/lib/colors';
import type { AmenityLevel, AdongDetail, AdongPark, AdongParksResponse, AdongScore } from '@/types/api';

interface AmenitySectionProps {
  amenities: AdongDetail['amenities'];
  allAdongs: AdongScore[] | undefined;
  currentAmenityScore: number;
  parks?: AdongParksResponse;
}

const LEVEL_BADGE: Record<AmenityLevel, { variant: 'success' | 'warning' | 'danger'; label: string }> = {
  sufficient: { variant: 'success', label: '충분' },
  normal: { variant: 'warning', label: '보통' },
  lacking: { variant: 'danger', label: '부족' },
};

const PARKS_DISPLAY_LIMIT = 6;
const WALK_METERS_PER_MIN = 67;

function dedupeParks(parks: AdongPark[]): AdongPark[] {
  const seen = new Map<string, AdongPark>();
  for (const p of parks) {
    if (!seen.has(p.id)) seen.set(p.id, p);
  }
  return Array.from(seen.values());
}


function formatParkName(name: string, category: string): string {
  const prefix = `${category}(`;
  if (!name.startsWith(prefix) || !name.endsWith(')')) return name;
  const inner = name.slice(prefix.length, -1).trim();
  return inner ? `${inner} ${category}` : name;
}

function formatArea(area_m2: number | null): string {
  if (area_m2 == null) return '면적 정보 없음';
  if (area_m2 >= 10_000) {
    const ha = area_m2 / 10_000;
    return `${ha.toFixed(1)} ha`;
  }
  return `${Math.round(area_m2).toLocaleString()}m²`;
}

function formatDistance(distance_m: number | null): string | null {
  if (distance_m == null) return null;
  if (distance_m < 1000) return `${Math.round(distance_m).toLocaleString()}m`;
  return `${(distance_m / 1000).toFixed(1)}km`;
}

function walkMinutes(distance_m: number | null): number | null {
  if (distance_m == null) return null;
  return Math.max(1, Math.ceil(distance_m / WALK_METERS_PER_MIN));
}

/** Amenity insight: count sufficient vs lacking categories. */
function getAmenityInsight(amenities: AdongDetail['amenities']): string | undefined {
  if (amenities.length === 0) return undefined;
  const sufficient = amenities.filter((a) => a.level === 'sufficient').length;
  const lacking = amenities.filter((a) => a.level === 'lacking').length;
  if (sufficient >= amenities.length * 0.6) return '대부분의 편의시설이 충분해요';
  if (lacking >= amenities.length * 0.4) return '일부 편의시설이 부족한 편이에요';
  return '편의시설이 평균적인 수준이에요';
}

export default function AmenitySection({
  amenities,
  allAdongs: _allAdongs,
  currentAmenityScore: _currentAmenityScore,
  parks,
}: AmenitySectionProps) {
  const dedupedParks = parks ? dedupeParks(parks.parks) : [];
  const sortedParks = [...dedupedParks].sort((a, b) => {
    const aa = a.area_m2 ?? -1;
    const bb = b.area_m2 ?? -1;
    return bb - aa;
  });
  const visibleParks = sortedParks.slice(0, PARKS_DISPLAY_LIMIT);
  const hasParks = parks != null && visibleParks.length > 0;

  const amenityInsight = getAmenityInsight(amenities);

  return (
    <div className="flex flex-col gap-2">
      {/* Amenity insight */}
      {amenityInsight && (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-primary-soft text-[13px] font-semibold text-primary">{amenityInsight}</span>
      )}

      {/* 1. Category table */}
      <Card padding="md">
        <h3 className="m-0 mb-1 text-[16px] leading-snug font-semibold text-text">
          카테고리별 편의시설
        </h3>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                <th className="bg-primary-soft text-text-subtle text-[11px] font-medium text-left py-2 px-3 border-b border-divider">
                  카테고리
                </th>
                <th className="bg-primary-soft text-text-subtle text-[11px] font-medium text-right py-2 px-3 border-b border-divider">
                  개수
                </th>
                <th className="bg-primary-soft text-text-subtle text-[11px] font-medium text-right py-2 px-3 border-b border-divider">
                  밀도(/km2)
                </th>
                <th className="bg-primary-soft text-text-subtle text-[11px] font-medium text-center py-2 px-3 border-b border-divider">
                  순위
                </th>
                <th className="bg-primary-soft text-text-subtle text-[11px] font-medium text-center py-2 px-3 border-b border-divider">
                  충분도
                </th>
              </tr>
            </thead>
            <tbody>
              {amenities.map((a) => {
                const badge = LEVEL_BADGE[a.level];
                return (
                  <tr key={a.category}>
                    <td className="py-2 px-3 border-b border-divider text-text font-medium">
                      {a.category}
                    </td>
                    <td className="tabular py-2 px-3 border-b border-divider text-text text-right">
                      {a.count.toLocaleString()}
                    </td>
                    <td className="tabular py-2 px-3 border-b border-divider text-text text-right">
                      {a.density_per_km2.toFixed(1)}
                    </td>
                    <td className="py-2 px-3 border-b border-divider text-center">
                      {a.percentile != null ? (
                        <span className="text-[11px] text-text-muted tabular">
                          TOP {a.percentile}%
                        </span>
                      ) : (
                        <span className="text-[11px] text-text-subtle">-</span>
                      )}
                    </td>
                    <td className="py-2 px-3 border-b border-divider text-center">
                      <Badge variant={badge.variant} size="sm">
                        {badge.label}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
              {amenities.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center text-text-muted py-6">
                    편의시설 데이터가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 2. Parks + Library placeholder — 2-column grid */}
      <div className="grid grid-cols-2 gap-2">
        {/* 3a. Parks (large parks TOP N) */}
        <Card padding="md">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              대형 공원
            </h3>
            {parks && parks.count > 0 && (
              <Badge variant="neutral" size="sm">
                총 {dedupedParks.length}곳
              </Badge>
            )}
          </div>

          {!hasParks ? (
            <div className="flex items-center justify-center h-[80px] text-text-muted text-[12px]">
              {parks ? '주변에 대형 공원이 없습니다' : '공원 정보를 불러오는 중입니다'}
            </div>
          ) : (
            <ul className="m-0 p-0 list-none flex flex-col gap-1.5">
              {visibleParks.map((p) => {
                const distLabel = formatDistance(p.distance_m);
                const walkMin = walkMinutes(p.distance_m);
                return (
                  <li
                    key={p.id}
                    className="flex items-center gap-2 p-2 rounded-card border border-divider bg-surface"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="flex-shrink-0 w-1.5 h-1.5 rounded-full"
                          style={{ backgroundColor: CATEGORY_COLORS.amenity }}
                          aria-hidden
                        />
                        <span className="text-[13px] font-medium text-text truncate">
                          {formatParkName(p.name, p.category)}
                        </span>
                      </div>
                      <p className="m-0 mt-0.5 text-[11px] text-text-muted truncate">
                        {p.category}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="tabular m-0 text-[13px] font-semibold text-text">
                        {formatArea(p.area_m2)}
                      </p>
                      {distLabel != null ? (
                        <p className="tabular m-0 mt-0.5 text-[11px] text-text-muted">
                          {distLabel}
                          {walkMin != null && (
                            <span className="ml-1 text-text-subtle">· 도보 {walkMin}분</span>
                          )}
                        </p>
                      ) : (
                        <p className="m-0 mt-0.5 text-[11px] text-text-subtle">
                          거리 정보 없음
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* 3b. Library placeholder */}
        <Card padding="md" className="opacity-60">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="m-0 text-[16px] leading-snug font-semibold text-text">
              도서관
            </h3>
            <Badge variant="neutral" size="sm">준비 중</Badge>
          </div>
          <div className="flex items-center justify-center py-6 text-text-muted text-[12px] text-center">
            도서관 위젯은 데이터 준비 중입니다
          </div>
        </Card>
      </div>
    </div>
  );
}
