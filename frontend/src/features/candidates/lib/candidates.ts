import { useCallback, useEffect, useState } from 'react';

import { readLocalStorage, writeLocalStorage } from '@/features/common/lib/browserStorage';
import { getUserCandidateRegions, saveUserCandidateRegions } from '@/features/common/lib/api';
import { useAuth } from '@/features/common/contexts/AuthContext';
import type { AdongScore, DashboardRegionIntro } from '@/features/common/types/api';

export type CandidateSource = 'conditions' | 'map' | 'detail';
export type CandidateRegionLevel = 'adong' | 'ldong';

export interface CandidateRegion {
  regionLevel: CandidateRegionLevel;
  slug: string;
  code?: string;
  gu: string;
  name: string;
  lat?: number;
  lng?: number;
  score?: number | null;
  score_rent?: number | null;
  score_transit?: number | null;
  score_amenity?: number | null;
  score_safety?: number | null;
  source: CandidateSource;
  addedAt: number;
}

const CANDIDATE_REGIONS_STORAGE_KEY = 'candidate.regions';
const CANDIDATE_REGIONS_SYNC_EVENT = 'candidate-regions-sync';
const CANDIDATE_REGIONS_CLEAR_PENDING_KEY = 'candidate.regions.clear.pending';
const CANDIDATE_REGIONS_REVISION_KEY = 'candidate.regions.revision';
const MAX_CANDIDATES = 10;

function storageKey(userId?: number | null) {
  return userId ? `${CANDIDATE_REGIONS_STORAGE_KEY}:user:${userId}` : CANDIDATE_REGIONS_STORAGE_KEY;
}

export function candidateKey(regionLevel: CandidateRegionLevel, slug: string) {
  return `${regionLevel}:${slug}`;
}

function parseCandidates(raw: string | null): CandidateRegion[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as CandidateRegion[];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) =>
        (item.regionLevel === 'adong' || item.regionLevel === 'ldong')
        && typeof item.slug === 'string'
        && typeof item.gu === 'string'
        && typeof item.name === 'string',
      )
      .slice(0, MAX_CANDIDATES);
  } catch {
    return [];
  }
}

export function loadCandidateRegions(userId?: number | null) {
  return parseCandidates(readLocalStorage(storageKey(userId)));
}

function emitCandidateRegionsSync() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(CANDIDATE_REGIONS_SYNC_EVENT));
}

function currentCandidateRevision() {
  return readLocalStorage(CANDIDATE_REGIONS_REVISION_KEY) ?? '0';
}

function bumpCandidateRevision() {
  const revision = `${Date.now()}:${Math.random().toString(36).slice(2)}`;
  writeLocalStorage(CANDIDATE_REGIONS_REVISION_KEY, revision);
  return revision;
}

function writeCandidateRegions(candidates: CandidateRegion[], userId?: number | null) {
  const value = JSON.stringify(candidates.slice(0, MAX_CANDIDATES));
  writeLocalStorage(storageKey(userId), value);
  if (userId) writeLocalStorage(CANDIDATE_REGIONS_STORAGE_KEY, JSON.stringify([]));
}

function saveCandidateRegions(candidates: CandidateRegion[], userId?: number | null, options?: { bumpRevision?: boolean }) {
  const shouldBump = options?.bumpRevision !== false;
  const revision = shouldBump ? bumpCandidateRevision() : currentCandidateRevision();
  writeCandidateRegions(candidates, userId);
  if (shouldBump && candidates.length > 0) clearClearPending();
  emitCandidateRegionsSync();
  return revision;
}

function candidateStorageKeys(userId?: number | null) {
  const keys = new Set<string>([CANDIDATE_REGIONS_STORAGE_KEY]);
  if (userId) keys.add(storageKey(userId));
  if (typeof window !== 'undefined') {
    try {
      for (let index = 0; index < window.localStorage.length; index += 1) {
        const key = window.localStorage.key(index);
        if (key?.startsWith(`${CANDIDATE_REGIONS_STORAGE_KEY}:user:`)) keys.add(key);
      }
    } catch {
      // Storage may be blocked; current session state still works.
    }
  }
  return [...keys];
}

function clearLocalCandidateRegions(userId?: number | null) {
  const revision = bumpCandidateRevision();
  if (typeof window === 'undefined') return revision;
  const empty = JSON.stringify([]);
  try {
    candidateStorageKeys(userId).forEach((key) => window.localStorage.setItem(key, empty));
    window.localStorage.setItem(CANDIDATE_REGIONS_CLEAR_PENDING_KEY, Date.now().toString());
  } catch {
    // Storage may be blocked; current session state still works.
  }
  emitCandidateRegionsSync();
  return revision;
}

function clearClearPending() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(CANDIDATE_REGIONS_CLEAR_PENDING_KEY);
  } catch {
    // Ignore storage failures.
  }
}

function hasPendingClear() {
  if (typeof window === 'undefined') return false;
  try {
    const raw = window.localStorage.getItem(CANDIDATE_REGIONS_CLEAR_PENDING_KEY);
    return Boolean(raw);
  } catch {
    return false;
  }
}

function sameCandidateList(left: CandidateRegion[], right: CandidateRegion[]) {
  if (left.length !== right.length) return false;
  return left.every((item, index) =>
    candidateKey(item.regionLevel, item.slug) === candidateKey(right[index].regionLevel, right[index].slug),
  );
}

export function candidateFromScore(
  region: AdongScore,
  regionLevel: CandidateRegionLevel,
  source: CandidateSource,
): CandidateRegion {
  return {
    regionLevel,
    slug: region.slug,
    code: region.code,
    gu: region.gu,
    name: region.name,
    lat: region.lat,
    lng: region.lng,
    score: region.score,
    score_rent: region.score_rent,
    score_transit: region.score_transit,
    score_amenity: region.score_amenity,
    score_safety: region.score_safety,
    source,
    addedAt: Date.now(),
  };
}

export function candidateFromIntro(
  intro: DashboardRegionIntro,
  source: CandidateSource,
  point?: { lat: number; lng: number },
): CandidateRegion {
  return {
    regionLevel: intro.type,
    slug: intro.slug,
    code: intro.code,
    gu: intro.gu_name,
    name: intro.dong_name,
    lat: point?.lat,
    lng: point?.lng,
    source,
    addedAt: Date.now(),
  };
}

export function candidateDetailPath(candidate: Pick<CandidateRegion, 'regionLevel' | 'slug'>) {
  return `/dashboard/${candidate.regionLevel}/${encodeURIComponent(candidate.slug)}`;
}

export function candidateMapPath(candidate: Pick<CandidateRegion, 'regionLevel' | 'slug' | 'lat' | 'lng' | 'gu' | 'name'>) {
  if (candidate.slug) {
    return `/map?mode=plain&region_level=${candidate.regionLevel}&region_slug=${encodeURIComponent(candidate.slug)}`;
  }
  if (typeof candidate.lat !== 'number' || typeof candidate.lng !== 'number') return '/map';
  const label = encodeURIComponent(`${candidate.gu} ${candidate.name}`);
  return `/map?mode=plain&ai_lat=${candidate.lat}&ai_lng=${candidate.lng}&ai_label=${label}`;
}

export function useCandidateRegions() {
  const { user, isLoading } = useAuth();
  const userId = user?.id ?? null;
  const [candidates, setCandidates] = useState<CandidateRegion[]>(() => (isLoading ? [] : loadCandidateRegions(userId)));

  const refresh = useCallback(() => {
    if (isLoading) {
      setCandidates([]);
      return;
    }
    setCandidates(loadCandidateRegions(userId));
  }, [isLoading, userId]);

  useEffect(() => {
    refresh();
    window.addEventListener('storage', refresh);
    window.addEventListener(CANDIDATE_REGIONS_SYNC_EVENT, refresh);
    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener(CANDIDATE_REGIONS_SYNC_EVENT, refresh);
    };
  }, [refresh]);

  useEffect(() => {
    if (isLoading || !userId) return;
    let cancelled = false;
    const requestRevision = currentCandidateRevision();
    const applyServerItems = (data: Awaited<ReturnType<typeof getUserCandidateRegions>>, clearSynced = false) => {
      if (cancelled) return;
      if (currentCandidateRevision() !== requestRevision) return;
      if (hasPendingClear() && !clearSynced) return;
      const serverItems = parseCandidates(JSON.stringify(data.items));
      saveCandidateRegions(serverItems, userId, { bumpRevision: false });
      setCandidates(serverItems);
      if (clearSynced) clearClearPending();
    };

    if (hasPendingClear()) {
      saveUserCandidateRegions([])
        .then((data) => applyServerItems(data, true))
        .catch(() => {
          // Keep local clear marker. Later mounts retry server deletion.
        });
      return () => {
        cancelled = true;
      };
    }

    getUserCandidateRegions()
      .then((data) => {
        applyServerItems(data);
      })
      .catch(() => {
        // Not logged in or network unavailable; local state still works.
      });
    return () => {
      cancelled = true;
    };
  }, [isLoading, userId]);

  const persistRemote = useCallback((next: CandidateRegion[], revision: string) => {
    if (!userId) return;
    saveUserCandidateRegions(next)
      .then((data) => {
        if (currentCandidateRevision() !== revision) return;
        if (!sameCandidateList(loadCandidateRegions(userId), next)) return;
        const serverItems = parseCandidates(JSON.stringify(data.items));
        saveCandidateRegions(serverItems, userId, { bumpRevision: false });
        setCandidates(serverItems);
        clearClearPending();
      })
      .catch(() => {
        // Keep local optimistic state; server sync can recover on next action.
      });
  }, [userId]);

  const addCandidate = useCallback((candidate: CandidateRegion) => {
    const current = loadCandidateRegions(userId);
    const key = candidateKey(candidate.regionLevel, candidate.slug);
    const existingIndex = current.findIndex((item) => candidateKey(item.regionLevel, item.slug) === key);
    const nextCandidate = { ...candidate, addedAt: Date.now() };
    const next = existingIndex >= 0
      ? current.map((item, index) => (index === existingIndex ? nextCandidate : item))
      : [nextCandidate, ...current].slice(0, MAX_CANDIDATES);
    const revision = saveCandidateRegions(next, userId);
    setCandidates(next);
    persistRemote(next, revision);
    return existingIndex >= 0 ? 'updated' : 'added';
  }, [persistRemote, userId]);

  const removeCandidate = useCallback((regionLevel: CandidateRegionLevel, slug: string) => {
    const key = candidateKey(regionLevel, slug);
    const next = loadCandidateRegions(userId).filter((item) => candidateKey(item.regionLevel, item.slug) !== key);
    const revision = next.length > 0 ? saveCandidateRegions(next, userId) : clearLocalCandidateRegions(userId);
    setCandidates(next);
    persistRemote(next, revision);
  }, [persistRemote, userId]);

  const clearCandidates = useCallback(() => {
    const revision = clearLocalCandidateRegions(userId);
    setCandidates([]);
    persistRemote([], revision);
  }, [persistRemote, userId]);

  const hasCandidate = useCallback(
    (regionLevel: CandidateRegionLevel, slug: string) => {
      const key = candidateKey(regionLevel, slug);
      return candidates.some((item) => candidateKey(item.regionLevel, item.slug) === key);
    },
    [candidates],
  );

  return {
    candidates,
    addCandidate,
    removeCandidate,
    clearCandidates,
    hasCandidate,
    maxCandidates: MAX_CANDIDATES,
  };
}
