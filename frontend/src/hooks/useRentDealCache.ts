import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';

import {
  getRentDealGridSummary,
  getRentDealGuCacheText,
  getRentDealGuCodes,
  getRentDealLdongSummary,
} from '@/lib/api';
import type {
  Bbox,
  ExploreDealType,
  MatchFilters,
  RentDealCachePin,
  RentDealCacheTypeCode,
  RentDealSummaryPin,
} from '@/types/api';
import type { MapState } from '@/components/Map/TransactionPinLayer';

const ONE_DAY_MS = 24 * 60 * 60 * 1000;
const DB_NAME = 'slgi-rent-deal-cache';
const DB_VERSION = 1;
const STORE_NAME = 'gu-tsv';
const TYPE_MAP: Record<RentDealCacheTypeCode, ExploreDealType> = {
  A: 'apt',
  O: 'officetel',
  Y: 'yeonlip',
  D: 'dasedae',
  V: 'yeonlip_dasedae',
  M: 'dagagu',
  H: 'danok',
};
const MAX_VISIBLE_RENT_PINS = 2500;

export type RentDealDisplayStage = 'hidden' | 'ldong' | 'grid' | 'cluster' | 'pin';

interface StoredGuCache {
  guCode: string;
  expiresAt: number;
  text: string;
}

export interface RentDealMapDataResult {
  stage: RentDealDisplayStage;
  pins: Array<RentDealSummaryPin | RentDealCachePin>;
  isFetching: boolean;
  isError: boolean;
  loadedGuCodes: string[];
}

export function rentDealStageForZoom(zoom: number | null | undefined): RentDealDisplayStage {
  if (typeof zoom !== 'number' || !Number.isFinite(zoom) || zoom < 12) return 'hidden';
  if (zoom < 14) return 'ldong';
  if (zoom < 16) return 'grid';
  if (zoom < 17) return 'cluster';
  return 'pin';
}

function bboxKey(bbox: Bbox | null | undefined): string {
  if (!bbox) return 'none';
  return [bbox.lng1, bbox.lat1, bbox.lng2, bbox.lat2].map((v) => v.toFixed(5)).join(',');
}

function periodToMinYmd(period: MatchFilters['period'], today: Date = new Date()): number | null {
  if (period === 'all') return null;
  const days = period === '3m' ? 90 : period === '6m' ? 180 : period === '12m' ? 365 : 730;
  const t = new Date(today);
  t.setDate(t.getDate() - days);
  return t.getFullYear() * 10000 + (t.getMonth() + 1) * 100 + t.getDate();
}

function expandDealTypesForFiltering(types: ExploreDealType[]): ExploreDealType[] {
  const expanded = [...types];
  if (types.includes('yeonlip') && types.includes('dasedae') && !expanded.includes('yeonlip_dasedae')) {
    expanded.push('yeonlip_dasedae');
  }
  return expanded;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME, { keyPath: 'guCode' });
    };
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function getStoredGuText(guCode: string): Promise<string | null> {
  if (!('indexedDB' in window)) return null;
  const db = await openDb();
  return new Promise<string | null>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const request = tx.objectStore(STORE_NAME).get(guCode);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const value = request.result as StoredGuCache | undefined;
      if (!value || value.expiresAt <= Date.now()) {
        resolve(null);
        return;
      }
      resolve(value.text);
    };
  }).finally(() => db.close());
}

async function setStoredGuText(guCode: string, text: string): Promise<void> {
  if (!('indexedDB' in window)) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).put({ guCode, text, expiresAt: Date.now() + ONE_DAY_MS } satisfies StoredGuCache);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  }).finally(() => db.close());
}

async function loadGuText(guCode: string): Promise<string> {
  const stored = await getStoredGuText(guCode);
  if (stored != null) return stored;
  const text = await getRentDealGuCacheText(guCode);
  await setStoredGuText(guCode, text);
  return text;
}

function parseGuPins(text: string, filters: MatchFilters, bbox: Bbox | null): RentDealCachePin[] {
  const expandedDealTypes = expandDealTypesForFiltering(filters.deal_types);
  const minYmd = periodToMinYmd(filters.period);
  const pins: RentDealCachePin[] = [];

  for (const line of text.split('\n')) {
    if (!line) continue;
    const [id, typeCode, depositRaw, monthlyRaw, convertedRaw, areaRaw, lngRaw, latRaw, ymdRaw] = line.split('\t');
    const lng = Number(lngRaw);
    const lat = Number(latRaw);
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;
    if (bbox && (lng < bbox.lng1 || lng > bbox.lng2 || lat < bbox.lat1 || lat > bbox.lat2)) continue;

    const contractYmd = Number(ymdRaw);
    if (minYmd != null && contractYmd < minYmd) continue;

    const dealType = TYPE_MAP[typeCode as RentDealCacheTypeCode];
    if (!dealType || !expandedDealTypes.includes(dealType)) continue;

    const deposit = Number(depositRaw);
    const monthlyRent = Number(monthlyRaw);
    const convertedRent = Number(convertedRaw);
    const areaM2 = areaRaw === '' ? null : Number(areaRaw);

    if (filters.filter_mode === 'raw') {
      if (deposit < filters.deposit_min || deposit > filters.deposit_max) continue;
      if (monthlyRent < filters.monthly_min || monthlyRent > filters.monthly_max) continue;
    } else if (convertedRent < filters.converted_min || convertedRent > filters.converted_max) {
      continue;
    }
    if (areaM2 != null && (areaM2 < filters.area_min || areaM2 > filters.area_max)) continue;

    pins.push({
      id,
      deal_type: dealType,
      area_m2: areaM2,
      deposit,
      monthly_rent: monthlyRent,
      converted_rent: convertedRent,
      lng,
      lat,
      contract_ymd: contractYmd,
    });
    if (pins.length >= MAX_VISIBLE_RENT_PINS) break;
  }

  return pins;
}

export function useRentDealCache(
  enabled: boolean,
  filters: MatchFilters,
  mapState: MapState | null,
): RentDealMapDataResult {
  const stage = rentDealStageForZoom(mapState?.zoom);
  const bbox = mapState?.bbox ?? null;
  const bboxQueryKey = bboxKey(bbox);

  const ldongQuery = useQuery({
    queryKey: ['rent-deals', 'summary', 'ldongs', filters],
    queryFn: () => getRentDealLdongSummary(filters),
    enabled: enabled && stage === 'ldong',
    staleTime: ONE_DAY_MS,
    gcTime: ONE_DAY_MS,
  });

  const gridQuery = useQuery({
    queryKey: ['rent-deals', 'summary', 'grids', filters, bboxQueryKey],
    queryFn: () => getRentDealGridSummary(filters, bbox),
    enabled: enabled && stage === 'grid',
    staleTime: ONE_DAY_MS,
    gcTime: ONE_DAY_MS,
  });

  const guCodesQuery = useQuery({
    queryKey: ['rent-deals', 'cache', 'gus', bboxQueryKey],
    queryFn: () => getRentDealGuCodes(bbox!),
    enabled: enabled && (stage === 'cluster' || stage === 'pin') && bbox != null,
    staleTime: ONE_DAY_MS,
    gcTime: ONE_DAY_MS,
  });

  const guCodes = useMemo(
    () => guCodesQuery.data?.items.map((item) => item.gu_code) ?? [],
    [guCodesQuery.data?.items],
  );

  const guChunkQueries = useQueries({
    queries: guCodes.map((guCode) => ({
      queryKey: ['rent-deals', 'cache', 'gu', guCode, filters, bboxQueryKey],
      queryFn: async () => parseGuPins(await loadGuText(guCode), filters, bbox),
      enabled: enabled && (stage === 'cluster' || stage === 'pin') && bbox != null,
      staleTime: ONE_DAY_MS,
      gcTime: ONE_DAY_MS,
    })),
  });

  const pins = useMemo(() => {
    if (stage === 'ldong') {
      return (ldongQuery.data?.rows ?? []).map<RentDealSummaryPin>(([code, guName, ldongName, avg, count, lng, lat]) => ({
        kind: 'ldong',
        id: code,
        label: ldongName,
        gu_name: guName,
        deal_type: 'yeonlip_dasedae',
        area_m2: null,
        deposit: 0,
        monthly_rent: 0,
        converted_rent: avg,
        count,
        lng,
        lat,
        contract_ymd: 0,
      }));
    }
    if (stage === 'grid') {
      return (gridQuery.data?.rows ?? []).map<RentDealSummaryPin>(([gridId, , guName, avg, count, lng, lat]) => ({
        kind: 'grid',
        id: gridId,
        label: '',
        gu_name: guName,
        deal_type: 'yeonlip_dasedae',
        area_m2: null,
        deposit: 0,
        monthly_rent: 0,
        converted_rent: avg,
        count,
        lng,
        lat,
        contract_ymd: 0,
      }));
    }
    if (stage === 'cluster' || stage === 'pin') {
      return guChunkQueries.flatMap((query) => query.data ?? []);
    }
    return [];
  }, [guChunkQueries, gridQuery.data?.rows, ldongQuery.data?.rows, stage]);

  return {
    stage,
    pins,
    loadedGuCodes: guCodes,
    isFetching:
      ldongQuery.isFetching ||
      gridQuery.isFetching ||
      guCodesQuery.isFetching ||
      guChunkQueries.some((query) => query.isFetching),
    isError:
      ldongQuery.isError ||
      gridQuery.isError ||
      guCodesQuery.isError ||
      guChunkQueries.some((query) => query.isError),
  };
}
