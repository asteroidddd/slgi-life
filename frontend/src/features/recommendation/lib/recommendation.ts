import { readSessionStorage, writeSessionStorage } from '@/features/common/lib/browserStorage';
import type { RecommendationRegionsResponse } from '@/features/common/types/api';

export type RecommendationPriority = 'budget' | 'transport';

export type RecommendationFacilityKey =
  | 'convenience'
  | 'daiso'
  | 'laundry'
  | 'park'
  | 'gym'
  | 'pharmacy'
  | 'hospital'
  | 'library'
  | 'study_cafe';

export interface RecommendationConditions {
  deposit: number;
  monthlyRent: number;
  areaM2: number | null;
  facilities: RecommendationFacilityKey[];
  universityId: string;
  universityName: string;
  maxCommuteMinutes: number;
  priority: RecommendationPriority;
}

export const RECOMMENDATION_CONDITIONS_STORAGE_KEY = 'recommendation.conditions';
export const RECOMMENDATION_RESULTS_STORAGE_KEY = 'recommendation.results';

export const RECOMMENDATION_FACILITY_GROUPS: Array<{
  group: string;
  items: Array<{
  key: RecommendationFacilityKey;
  label: string;
  }>;
}> = [
  {
    group: '생활',
    items: [
      { key: 'convenience', label: '편의점' },
      { key: 'daiso', label: '다이소' },
      { key: 'laundry', label: '셀프빨래방' },
    ],
  },
  {
    group: '운동',
    items: [
      { key: 'park', label: '공원' },
      { key: 'gym', label: '헬스장' },
    ],
  },
  {
    group: '의료',
    items: [
      { key: 'pharmacy', label: '약국' },
      { key: 'hospital', label: '병원' },
    ],
  },
  {
    group: '공부',
    items: [
      { key: 'library', label: '도서관' },
      { key: 'study_cafe', label: '스터디카페' },
    ],
  },
];

export const RECOMMENDATION_FACILITIES = RECOMMENDATION_FACILITY_GROUPS.flatMap((group) => group.items);

export function saveRecommendationConditions(conditions: RecommendationConditions) {
  writeSessionStorage(
    RECOMMENDATION_CONDITIONS_STORAGE_KEY,
    JSON.stringify(conditions),
  );
}

export function recommendationConditionsSignature(conditions: RecommendationConditions) {
  return JSON.stringify({
    deposit: conditions.deposit,
    monthlyRent: conditions.monthlyRent,
    areaM2: conditions.areaM2,
    facilities: [...conditions.facilities].sort(),
    universityId: conditions.universityId,
    maxCommuteMinutes: conditions.maxCommuteMinutes,
    priority: conditions.priority,
  });
}

export function saveRecommendationResults(
  conditions: RecommendationConditions,
  result: RecommendationRegionsResponse,
) {
  writeSessionStorage(
    RECOMMENDATION_RESULTS_STORAGE_KEY,
    JSON.stringify({
      signature: recommendationConditionsSignature(conditions),
      result,
      savedAt: Date.now(),
    }),
  );
}

export function loadRecommendationResults(
  conditions: RecommendationConditions | null,
): RecommendationRegionsResponse | null {
  if (!conditions) return null;
  const raw = readSessionStorage(RECOMMENDATION_RESULTS_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as {
      signature?: string;
      result?: RecommendationRegionsResponse;
    };
    if (parsed.signature !== recommendationConditionsSignature(conditions)) return null;
    if (!parsed.result || !Array.isArray(parsed.result.adongs) || !Array.isArray(parsed.result.ldongs)) return null;
    return parsed.result;
  } catch {
    return null;
  }
}

export function loadRecommendationConditions(): RecommendationConditions | null {
  const raw = readSessionStorage(RECOMMENDATION_CONDITIONS_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<RecommendationConditions>;
    if (
      typeof parsed.deposit !== 'number'
      || typeof parsed.monthlyRent !== 'number'
      || typeof parsed.maxCommuteMinutes !== 'number'
      || (parsed.priority !== 'budget' && parsed.priority !== 'transport')
    ) {
      return null;
    }
    return {
      deposit: parsed.deposit,
      monthlyRent: parsed.monthlyRent,
      areaM2: typeof parsed.areaM2 === 'number' ? parsed.areaM2 : null,
      facilities: Array.isArray(parsed.facilities)
        ? parsed.facilities.filter((item): item is RecommendationFacilityKey =>
          RECOMMENDATION_FACILITIES.some((facility) => facility.key === item),
        )
        : [],
      universityId: typeof parsed.universityId === 'string' ? parsed.universityId : '',
      universityName: typeof parsed.universityName === 'string' ? parsed.universityName : '',
      maxCommuteMinutes: parsed.maxCommuteMinutes,
      priority: parsed.priority,
    };
  } catch {
    return null;
  }
}
