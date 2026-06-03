import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';

import AmenityLayer from '@/features/map/components/AmenityLayer';
import HeatMap from '@/features/map/components/HeatMap';
import type { ScoreLayerKey } from '@/features/map/components/HeatMap';
import {
  FilterButton,
  IconTooltip,
  ResetButton,
} from '@/features/map/components/MapControls';
import {
  AiMapTargetLayer,
  CurrentLocationLayer,
  HomeLocationLayer,
  HomeMarker,
  MapClickSelectLayer,
  MapStateProbe,
  SavedLocationFlyToLayer,
  SearchFlyTo,
  SelectedPlacePinLayer,
  hasValidCoordinate,
  type MapState,
} from '@/features/map/components/MapInteractionLayers';
import type { SelectedPlacePin } from '@/features/map/components/MapInteractionLayers';
import MapPopup, { buildScoreRanks, type SelectedPopup } from '@/features/map/components/MapPopup';
import MedicalControlPanel, { type MedicalCategory } from '@/features/map/components/MedicalControlPanel';
import daisoLogo from '@/assets/logos/facilities/daiso.svg';
import oliveyoungLogo from '@/assets/logos/facilities/oliveyoung.svg';
import { candidateFromIntro, candidateFromScore, useCandidateRegions } from '@/features/candidates/lib/candidates';
import { useAuth } from '@/features/common/contexts/AuthContext';
import Tooltip from '@/features/common/components/ui/Tooltip';
import { useAdongScores, useLdongScores } from '@/features/common/hooks/useAdongs';
import { getAmenitiesBbox, getDashboardRegionAtPoint, getMapSearch, getMedicalFacilities, getMedicalSpecialtyGroups } from '@/features/common/lib/api';
import { HEATMAP_COLORS_ORDERED } from '@/features/common/lib/colors';
import { getSavedMapView, saveMapView } from '@/features/map/lib/mapViewMemory';
import { DEFAULT_WEIGHTS } from '@/features/common/types/api';
import type { AdongScore, MapSearchItem } from '@/features/common/types/api';

import 'leaflet/dist/leaflet.css';

type RegionLevel = 'adong' | 'ldong';

type FacilityKey =
  | 'subway_station'
  | 'bus_stop'
  | 'park'
  | 'library'
  | 'convenience'
  | 'daiso'
  | 'restaurant'
  | 'cafe'
  | 'laundry'
  | 'oliveyoung'
  | 'gym'
  | 'study_cafe';

interface AiMapTarget {
  label: string;
  lat: number;
  lng: number;
}

interface MapBbox {
  lng1: number;
  lat1: number;
  lng2: number;
  lat2: number;
}

const SEOUL_AI_TARGET_BOUNDS = {
  minLat: 37.35,
  maxLat: 37.75,
  minLng: 126.7,
  maxLng: 127.3,
};

const HOME_MARKER_VISIBILITY_STORAGE_KEY = 'map.homeMarker.visible';

const HEAT_LAYERS: Array<{ key: ScoreLayerKey; label: string; title: string }> = [
  { key: 'composite', label: '종합 점수', title: '부동산, 교통, 편의시설 점수를 합산한 값입니다.' },
  { key: 'rent', label: '부동산 점수', title: '최근 실거래 기반 환산월세 지표입니다.' },
  { key: 'transit', label: '교통 점수', title: '지하철역 거리와 버스정류장 밀도를 합산합니다.' },
  { key: 'amenity', label: '편의시설 점수', title: '생활시설, 의료시설, 공원 지표를 합산합니다.' },
  { key: 'safety', label: '안전 지수', title: '지역안전등급 원자료를 점수화한 지표입니다.' },
];

const FACILITY_LABELS: Record<FacilityKey, string> = {
  subway_station: '지하철역',
  bus_stop: '버스정류장',
  park: '공원',
  library: '도서관',
  convenience: '편의점',
  daiso: '다이소',
  restaurant: '음식점',
  cafe: '카페',
  laundry: '셀프 빨래방',
  oliveyoung: '올리브영',
  gym: '헬스장',
  study_cafe: '스터디카페',
};

const FACILITY_ORDER: FacilityKey[] = [
  'subway_station',
  'bus_stop',
  'park',
  'library',
  'convenience',
  'daiso',
  'restaurant',
  'cafe',
  'laundry',
  'oliveyoung',
  'gym',
  'study_cafe',
];

const MEDICAL_CATEGORY_ORDER: MedicalCategory[] = ['hospital', 'dental', 'pharmacy', 'emergency'];

function facilityLogoIcon(src: string, label: string) {
  return `<img src="${src}" alt="${label}" style="display:block;width:16px;height:16px;object-fit:contain;border-radius:4px;" />`;
}

const FACILITY_ICONS: Record<FacilityKey, string> = {
  subway_station: '🚇',
  bus_stop: '🚌',
  park: '🌳',
  library: '📚',
  convenience: '🏪',
  daiso: facilityLogoIcon(daisoLogo, '다이소'),
  restaurant: '🍜',
  cafe: '☕',
  laundry: '🧺',
  oliveyoung: facilityLogoIcon(oliveyoungLogo, '올리브영'),
  gym: '🏋',
  study_cafe: '📖',
};

function isValidAiMapCoordinate(lat: number, lng: number) {
  return Number.isFinite(lat)
    && Number.isFinite(lng)
    && !(lat === 0 && lng === 0)
    && lat >= SEOUL_AI_TARGET_BOUNDS.minLat
    && lat <= SEOUL_AI_TARGET_BOUNDS.maxLat
    && lng >= SEOUL_AI_TARGET_BOUNDS.minLng
    && lng <= SEOUL_AI_TARGET_BOUNDS.maxLng;
}

export default function MainMap() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const { addCandidate } = useCandidateRegions();
  const [regionLevel, setRegionLevel] = useState<RegionLevel>(() => searchParams.get('region_level') === 'adong' ? 'adong' : 'ldong');
  const [heatmapEnabled, setHeatmapEnabled] = useState(false);
  const [heatLayer, setHeatLayer] = useState<ScoreLayerKey>('composite');
  const [selectedMapRegionSlug, setSelectedMapRegionSlug] = useState<string | null>(() => searchParams.get('region_slug'));
  const [selectedMapRegionLevel, setSelectedMapRegionLevel] = useState<RegionLevel>(() => searchParams.get('region_level') === 'adong' ? 'adong' : 'ldong');
  const [facilityKeys, setFacilityKeys] = useState<Set<FacilityKey>>(() => new Set());
  const [medicalCategories, setMedicalCategories] = useState<Set<MedicalCategory>>(() => new Set());
  const [medicalSpecialtyGroups, setMedicalSpecialtyGroups] = useState<Set<string>>(() => new Set());
  const [medicalOpenNow, setMedicalOpenNow] = useState(false);
  const [mapState, setMapState] = useState<MapState | null>(null);
  const savedMapView = useMemo(() => getSavedMapView(), []);
  const [popup, setPopup] = useState<SelectedPopup>(null);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<MapSearchItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedSearchItem, setSelectedSearchItem] = useState<MapSearchItem | null>(null);
  const [selectedPlacePin, setSelectedPlacePin] = useState<SelectedPlacePin | null>(null);
  const [activeAiMapTarget, setActiveAiMapTarget] = useState<AiMapTarget | null>(null);
  const aiMapTarget = useMemo<AiMapTarget | null>(() => {
    const lat = Number(searchParams.get('ai_lat'));
    const lng = Number(searchParams.get('ai_lng'));
    if (!isValidAiMapCoordinate(lat, lng)) return null;
    return {
      lat,
      lng,
      label: searchParams.get('ai_label') || 'AI 추천 위치',
    };
  }, [searchParams]);
  const [toast, setToast] = useState<string | null>(null);
  const [locateRequest, setLocateRequest] = useState(0);
  const [homeRequest, setHomeRequest] = useState(0);
  const [schoolRequest, setSchoolRequest] = useState(0);
  const [showHomeMarker, setShowHomeMarker] = useState(() => {
    try {
      return window.localStorage.getItem(HOME_MARKER_VISIBILITY_STORAGE_KEY) !== 'false';
    } catch {
      return true;
    }
  });
  const toastTimer = useRef<number | null>(null);
  const mapStateRef = useRef<MapState | null>(null);

  const adongScoresQuery = useAdongScores(DEFAULT_WEIGHTS);
  const ldongScoresQuery = useLdongScores(DEFAULT_WEIGHTS);
  const scoresData = regionLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
  const scoresLoading = regionLevel === 'ldong' ? ldongScoresQuery.isLoading : adongScoresQuery.isLoading;
  const scoresError = regionLevel === 'ldong' ? ldongScoresQuery.isError : adongScoresQuery.isError;
  const selectedBoundaryScores = selectedMapRegionLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
  const ranks = useMemo(() => buildScoreRanks(scoresData), [scoresData]);

  const activeFacilityBbox = useMemo<MapBbox | null>(() => {
    if (!mapState?.bbox) return null;
    return mapState.bbox;
  }, [mapState?.bbox]);
  const selectedFacilityCategories = useMemo(() => Array.from(facilityKeys), [facilityKeys]);
  const amenitiesQuery = useQuery({
    queryKey: [
      'amenities',
      'bbox',
      activeFacilityBbox?.lng1,
      activeFacilityBbox?.lat1,
      activeFacilityBbox?.lng2,
      activeFacilityBbox?.lat2,
      selectedFacilityCategories.join(','),
    ],
    queryFn: () => getAmenitiesBbox({
      bbox: [
        activeFacilityBbox!.lng1,
        activeFacilityBbox!.lat1,
        activeFacilityBbox!.lng2,
        activeFacilityBbox!.lat2,
      ],
      categories: selectedFacilityCategories,
    }),
    enabled: activeFacilityBbox != null && selectedFacilityCategories.length > 0,
    staleTime: 60_000,
  });
  const visibleAmenities = useMemo(() => {
    if (selectedFacilityCategories.length === 0) return [];
    const selected = new Set(selectedFacilityCategories);
    return (amenitiesQuery.data?.items ?? []).filter((item) => selected.has(item.category as FacilityKey));
  }, [amenitiesQuery.data?.items, selectedFacilityCategories]);

  const selectedMedicalCategories = useMemo(
    () => MEDICAL_CATEGORY_ORDER.filter((key) => medicalCategories.has(key)),
    [medicalCategories],
  );
  const selectedMedicalSpecialtyGroups = useMemo(
    () => Array.from(medicalSpecialtyGroups),
    [medicalSpecialtyGroups],
  );
  const medicalSpecialtyGroupsQuery = useQuery({
    queryKey: ['medical', 'specialty-groups', 'hospital'],
    queryFn: () => getMedicalSpecialtyGroups({ category: 'hospital' }),
    staleTime: 300_000,
  });
  const medicalBbox = mapState?.bbox ?? null;
  const medicalFacilitiesQueries = useQueries({
    queries: selectedMedicalCategories.map((category) => ({
      queryKey: [
        'medical',
        'facilities',
        medicalBbox?.lng1,
        medicalBbox?.lat1,
        medicalBbox?.lng2,
        medicalBbox?.lat2,
        category,
        category === 'hospital' ? selectedMedicalSpecialtyGroups.join(',') : '',
        medicalOpenNow,
      ],
      queryFn: () => getMedicalFacilities({
        bbox: [
          medicalBbox!.lng1,
          medicalBbox!.lat1,
          medicalBbox!.lng2,
          medicalBbox!.lat2,
        ],
        categories: [category],
        specialtyGroups: category === 'hospital' ? selectedMedicalSpecialtyGroups : undefined,
        openNow: medicalOpenNow,
      }),
      enabled: medicalBbox != null,
      staleTime: 60_000,
    })),
  });
  const medicalFacilitiesFetching = medicalFacilitiesQueries.some((query) => query.isFetching);
  const visibleMedicalFacilities = useMemo(() => {
    if (selectedMedicalCategories.length === 0) return [];
    const selected = new Set(selectedMedicalCategories);
    const seen = new Set<string>();
    const items = [];
    for (const query of medicalFacilitiesQueries) {
      for (const item of query.data?.items ?? []) {
        if (!selected.has(item.category as MedicalCategory) || seen.has(item.hpid)) continue;
        seen.add(item.hpid);
        items.push(item);
      }
    }
    return items;
  }, [medicalFacilitiesQueries, selectedMedicalCategories]);

  const heatmapActiveLayer: ScoreLayerKey = heatLayer;
  const hasHomeLocation = !!user
    && typeof user.home_lat === 'number'
    && Number.isFinite(user.home_lat)
    && typeof user.home_lng === 'number'
    && Number.isFinite(user.home_lng);
  const hasSchoolLocation = !!user
    && typeof user.school_lat === 'number'
    && Number.isFinite(user.school_lat)
    && typeof user.school_lng === 'number'
    && Number.isFinite(user.school_lng);

  const flash = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => {
      setToast(null);
      toastTimer.current = null;
    }, 2200);
  }, []);

  useEffect(() => () => {
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    const q = searchText.trim();
    if (q.length < 2) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }
    let cancelled = false;
    setSearchLoading(true);
    const timer = window.setTimeout(() => {
      getMapSearch(q)
        .then((data) => { if (!cancelled) setSearchResults(data.items); })
        .catch(() => { if (!cancelled) setSearchResults([]); })
        .finally(() => { if (!cancelled) setSearchLoading(false); });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchText]);

  useEffect(() => {
    try {
      window.localStorage.setItem(HOME_MARKER_VISIBILITY_STORAGE_KEY, showHomeMarker ? 'true' : 'false');
    } catch {
      // Storage may be blocked; current session toggle still works.
    }
  }, [showHomeMarker]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      let handled = false;
      if (popup) {
        setPopup(null);
        handled = true;
      }
      if (searchResults.length > 0 || searchLoading) {
        setSearchResults([]);
        setSearchLoading(false);
        handled = true;
      }
      if (handled) event.preventDefault();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [popup, searchResults.length, searchLoading]);

  useEffect(() => {
    const hasAiParams = searchParams.has('ai_lat') || searchParams.has('ai_lng') || searchParams.has('ai_label');
    if (!hasAiParams) return;
    if (aiMapTarget) {
      setActiveAiMapTarget(aiMapTarget);
      setHeatmapEnabled(false);
    } else {
      setActiveAiMapTarget(null);
    }
    const next = new URLSearchParams(searchParams);
    next.delete('ai_lat');
    next.delete('ai_lng');
    next.delete('ai_label');
    next.set('mode', 'plain');
    setSearchParams(next, { replace: true });
  }, [aiMapTarget, searchParams, setSearchParams]);

  useEffect(() => {
    const level = searchParams.get('region_level');
    const slug = searchParams.get('region_slug');
    const validLevel = level === 'adong' || level === 'ldong' ? level : null;
    if (validLevel && !slug) {
      setRegionLevel(validLevel);
    }
    if (slug) {
      setSelectedMapRegionSlug(slug);
      setSelectedMapRegionLevel(validLevel ?? 'ldong');
      setHeatmapEnabled(false);
      setPopup(null);
    }
  }, [searchParams]);

  const persistMapView = useCallback((state?: MapState | null) => {
    const targetState = state ?? mapStateRef.current;
    if (!targetState?.bbox || typeof targetState.zoom !== 'number') return;
    saveMapView({
      center: [
        (targetState.bbox.lat1 + targetState.bbox.lat2) / 2,
        (targetState.bbox.lng1 + targetState.bbox.lng2) / 2,
      ],
      zoom: targetState.zoom,
      mode: heatmapEnabled ? 'heatmap' : 'plain',
    });
  }, [heatmapEnabled]);

  const handleMapStateChange = useCallback((state: MapState) => {
    mapStateRef.current = state;
    setMapState(state);
    persistMapView(state);
  }, [persistMapView]);

  const openRegionDashboard = useCallback((region: AdongScore) => {
    persistMapView();
    navigate(`/dashboard/${regionLevel}/${encodeURIComponent(region.slug)}`);
  }, [navigate, persistMapView, regionLevel]);

  const addRegionCandidate = useCallback((region: AdongScore) => {
    addCandidate(candidateFromScore(region, regionLevel, 'map'));
    flash(`${region.gu} ${region.name}을 담았습니다.`);
  }, [addCandidate, flash, regionLevel]);

  const addCandidateForPoint = useCallback(async (lat: number, lng: number) => {
    try {
      const region = await getDashboardRegionAtPoint(regionLevel, lat, lng);
      const scoreSource = region.type === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
      const scoredRegion = scoreSource.find((item) => item.slug === region.slug);
      addCandidate(scoredRegion
        ? candidateFromScore(scoredRegion, region.type, 'map')
        : candidateFromIntro(region, 'map', { lat, lng }));
      flash(`${region.gu_name} ${region.dong_name}을 담았습니다.`);
    } catch {
      flash('현재 위치의 법정동을 찾지 못했습니다.');
    }
  }, [addCandidate, adongScoresQuery.data, flash, ldongScoresQuery.data, regionLevel]);

  const openDashboardForPoint = useCallback(async (lat: number, lng: number) => {
    persistMapView();
    try {
      const region = await getDashboardRegionAtPoint(regionLevel, lat, lng);
      navigate(region.slug ? `/dashboard/${region.type}/${encodeURIComponent(region.slug)}` : `/dashboard/${regionLevel}`);
    } catch {
      flash('현재 위치의 법정동을 찾지 못했습니다.');
    }
  }, [flash, navigate, persistMapView, regionLevel]);

  const selectRegionAtPoint = useCallback(async (lat: number, lng: number, source: SelectedPlacePin['source']) => {
    setSelectedMapRegionSlug(null);
    try {
      const region = await getDashboardRegionAtPoint(regionLevel, lat, lng);
      setSelectedPlacePin({
        lat,
        lng,
        label: `${region.gu_name} ${region.dong_name}`,
        source,
        regionLevel: region.type,
        slug: region.slug,
        gu: region.gu_name,
        name: region.dong_name,
      });
    } catch {
      setSelectedPlacePin({ lat, lng, label: '선택한 위치', source });
      flash('현재 위치의 동네를 찾지 못했습니다.');
    }
  }, [flash, regionLevel]);

  const handleHeatLayerSelect = (layer: ScoreLayerKey) => {
    const turningOff = heatmapEnabled && heatLayer === layer;
    setHeatLayer(layer);
    setHeatmapEnabled(!turningOff);
    setPopup(null);
    const next = new URLSearchParams(searchParams);
    next.delete('region_level');
    next.delete('region_slug');
    if (turningOff) next.set('mode', 'plain');
    else {
      next.delete('mode');
      next.set('heat_layer', layer);
    }
    setSearchParams(next, { replace: true });
  };

  const toggleFacility = (key: FacilityKey) => {
    setPopup(null);
    setFacilityKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleMedicalCategory = (key: MedicalCategory) => {
    setPopup(null);
    setMedicalCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleMedicalSpecialtyGroup = (name: string) => {
    setPopup(null);
    setMedicalCategories((prev) => {
      const next = new Set(prev);
      next.add('hospital');
      return next;
    });
    setMedicalSpecialtyGroups((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectSearchItem = (item: MapSearchItem) => {
    if (!hasValidCoordinate(item)) {
      flash('좌표가 없는 검색 결과입니다.');
      return;
    }
    setSelectedSearchItem(item);
    setSelectedMapRegionSlug(null);
    setSelectedPlacePin({ lat: item.lat, lng: item.lng, label: item.name, source: 'search' });
    setPopup(null);
    setSearchText(item.name);
    setSearchResults([]);
  };

  return (
    <main className="map-redesign relative h-screen w-screen overflow-hidden bg-bg text-text">
      <h1 className="sr-only">서울 주거 지도</h1>

      <HeatMap
        adongs={scoresData}
        activeLayer={heatmapActiveLayer}
        heatmapVisible={heatmapEnabled}
        regionLevel={regionLevel}
        selectedRegionSlug={selectedMapRegionSlug}
        selectedRegionLevel={selectedMapRegionLevel}
        selectedRegionAdongs={selectedBoundaryScores}
        selectedRegionFocusKey={searchParams.get('focus')}
        initialCenter={savedMapView?.center}
        initialZoom={savedMapView?.zoom}
        onAdongClick={heatmapEnabled ? (adong) => setPopup({ type: 'adong', adong }) : undefined}
      >
        <CurrentLocationLayer
          requestId={locateRequest}
          onError={(message) => flash(message)}
          onLocated={(lat, lng) => {
            setSelectedSearchItem(null);
            setPopup(null);
            setSelectedPlacePin({ lat, lng, label: '현재 위치', source: 'current-location' });
          }}
        />
        <HomeLocationLayer
          requestId={homeRequest}
          lat={user?.home_lat}
          lng={user?.home_lng}
          onError={(message) => flash(message)}
          onLocated={(lat, lng) => {
            setSelectedSearchItem(null);
            setPopup(null);
            setSelectedPlacePin({ lat, lng, label: '집', source: 'home' });
          }}
        />
        <SavedLocationFlyToLayer
          requestId={schoolRequest}
          lat={user?.school_lat}
          lng={user?.school_lng}
          missingMessage="마이페이지에서 대학을 저장해주세요."
          onError={(message) => flash(message)}
          onLocated={() => {
            setSelectedSearchItem(null);
            setPopup(null);
          }}
        />
        <SearchFlyTo item={selectedSearchItem} />
        <MapClickSelectLayer
          enabled={!heatmapEnabled}
          onSelect={(pin) => {
            setSelectedSearchItem(null);
            setPopup(null);
            void selectRegionAtPoint(pin.lat, pin.lng, pin.source);
          }}
        />
        {!heatmapEnabled ? (
          <SelectedPlacePinLayer
            pin={selectedPlacePin}
            onCandidateClick={(pin) => void addCandidateForPoint(pin.lat, pin.lng)}
            onDetailClick={(pin) => void openDashboardForPoint(pin.lat, pin.lng)}
            onClear={() => setSelectedPlacePin(null)}
          />
        ) : null}
        <AiMapTargetLayer target={activeAiMapTarget} />
        {showHomeMarker ? (
          <HomeMarker
            lat={user?.home_lat}
            lng={user?.home_lng}
            onClick={() => setPopup({ type: 'home', address: user?.address })}
          />
        ) : null}
        <MapStateProbe onMapStateChange={handleMapStateChange} />
        <AmenityLayer
          items={visibleAmenities}
          getIcon={(category) => FACILITY_ICONS[category as FacilityKey] ?? '•'}
          onSelect={(item) => setPopup({
            type: 'facility',
            title: item.name,
            description: FACILITY_LABELS[item.category as FacilityKey] ?? item.category,
          })}
        />
        <AmenityLayer
          items={visibleMedicalFacilities}
          getIcon={(category) => {
            const icons: Record<string, string> = { hospital: '🏥', dental: '🦷', pharmacy: '💊', emergency: '🚑' };
            return icons[category] ?? 'M';
          }}
          onSelect={(item) => {
            if (!('hpid' in item)) return;
            const detail = [
              item.category === 'emergency' ? '응급실' : item.type,
              item.address,
              item.tel1,
            ].filter(Boolean).join(' · ');
            setPopup({
              type: 'facility',
              title: item.name,
              description: detail,
            });
          }}
        />
      </HeatMap>

      <section className="pointer-events-none absolute left-5 top-5 z-[500] flex max-h-[calc(100vh-96px)] w-[430px] flex-col gap-2 overflow-visible" aria-label="지도 검색과 필터">
        <div className="pointer-events-auto relative z-[700] w-full">
          <label className="flex h-11 w-full items-center gap-3 rounded-card border border-border bg-surface/95 px-3 shadow-lg backdrop-blur">
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-[18px] font-semibold text-text-muted" aria-hidden="true">⌕</span>
            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && searchResults[0]) {
                  selectSearchItem(searchResults[0]);
                }
              }}
              placeholder="지역, 지하철역, 학교 등 검색"
              className="min-w-0 flex-1 border-0 bg-transparent text-[14px] outline-none placeholder:text-text-subtle"
            />
            {searchText ? (
              <button
                type="button"
                aria-label="검색어 지우기"
                title="검색어 지우기"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  setSearchText('');
                  setSearchResults([]);
                  setSearchLoading(false);
                }}
                className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[18px] font-semibold leading-none text-text-subtle transition hover:bg-surface-alt hover:text-text"
              >
                ×
              </button>
            ) : null}
          </label>
          {(searchLoading || searchResults.length > 0) ? (
            <div className="absolute left-0 top-[calc(100%+6px)] z-[650] max-h-[min(360px,calc(100vh-120px))] w-full overflow-y-auto rounded-card border border-border bg-surface/95 shadow-xl backdrop-blur">
              {searchLoading ? <div className="px-3 py-2 text-[13px] font-semibold text-text-muted">검색 중...</div> : null}
              {searchResults.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => selectSearchItem(item)}
                  className="block w-full border-t border-border/70 px-3 py-2 text-left transition first:border-t-0 hover:bg-[var(--color-heatmap-1)]"
                >
                  <span className="block text-[13px] font-semibold text-text">{item.name}</span>
                  <span className="mt-0.5 block truncate text-[12px] text-text-muted">{item.label}{item.address ? ' · ' + item.address : ''}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="pointer-events-none grid max-h-[calc(100vh-150px)] grid-cols-[152px_152px] items-start justify-items-start gap-2 overflow-y-auto pr-1">
          <div className="pointer-events-auto grid w-[152px] self-start grid-cols-1 justify-items-start gap-1 overflow-visible rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur" aria-label="생활시설">
            {FACILITY_ORDER.map((key) => (
              <FilterButton key={key} active={facilityKeys.has(key)} onClick={() => toggleFacility(key)} className="w-full">
                <span className="inline-flex h-full translate-y-px items-center gap-1.5 leading-none">
                  <span aria-hidden="true" className="inline-flex h-4 w-4 shrink-0 items-center justify-center leading-none" dangerouslySetInnerHTML={{ __html: FACILITY_ICONS[key] }} />
                  <span className="leading-none">{FACILITY_LABELS[key]}</span>
                </span>
              </FilterButton>
            ))}
            <div className="w-full">
              <ResetButton onClick={() => { setPopup(null); setFacilityKeys(new Set()); }}>초기화</ResetButton>
            </div>
          </div>

          <MedicalControlPanel
            categories={medicalCategories}
            specialtyGroups={medicalSpecialtyGroupsQuery.data?.items.map((item) => item.name) ?? []}
            selectedSpecialtyGroups={medicalSpecialtyGroups}
            openNow={medicalOpenNow}
            onToggleCategory={toggleMedicalCategory}
            onToggleSpecialtyGroup={toggleMedicalSpecialtyGroup}
            onResetSpecialtyGroups={() => setMedicalSpecialtyGroups(new Set())}
            onToggleOpenNow={() => setMedicalOpenNow((value) => !value)}
            onReset={() => {
              setPopup(null);
              setMedicalCategories(new Set());
              setMedicalSpecialtyGroups(new Set());
              setMedicalOpenNow(false);
            }}
          />
        </div>
      </section>

      <section className="pointer-events-none absolute left-1/2 top-5 z-[520] flex -translate-x-1/2 justify-center" aria-label="히트맵 설정">
        <div className="pointer-events-auto flex max-w-[calc(100vw-560px)] flex-wrap items-center justify-center gap-1 rounded-card border border-border bg-surface/95 p-1 shadow-lg backdrop-blur">
          <span className="px-2 text-[12px] font-extrabold text-text">히트맵</span>
          <span className="group relative inline-flex">
            <button
              type="button"
              className="h-5 w-5 rounded-full border border-border bg-surface-alt text-[10px] font-bold leading-none text-text-muted transition hover:border-primary hover:text-primary"
              aria-label="히트맵 설명"
            >
              i
            </button>
            <span className="app-tooltip app-tooltip--info app-tooltip--muted pointer-events-none absolute left-1/2 top-[calc(100%+8px)] z-[var(--tooltip-z)] hidden w-[260px] -translate-x-1/2 text-left group-hover:block group-focus-within:block">
              점수 항목을 선택하면 해당 기준의 동네별 색상 지도가 켜집니다. 아무 점수도 선택하지 않으면 기본 지도와 선택 경계만 표시됩니다.
            </span>
          </span>
          <button type="button" onClick={() => setRegionLevel('adong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'adong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>행정동</button>
          <button type="button" onClick={() => setRegionLevel('ldong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'ldong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>법정동</button>
          <span className="h-5 w-px bg-divider" aria-hidden="true" />
          {HEAT_LAYERS.map((layer) => (
            <Tooltip key={layer.key} label={layer.title} placement="bottom">
              <button
                type="button"
                onClick={() => handleHeatLayerSelect(layer.key)}
                aria-pressed={heatmapEnabled && heatLayer === layer.key}
                className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${
                  heatLayer === layer.key && heatmapEnabled
                    ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm'
                    : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'
                }`}
              >
                {layer.label}
              </button>
            </Tooltip>
          ))}
        </div>
      </section>

      <div className="absolute bottom-6 left-6 z-[500] flex items-center gap-2">
        <span className="group relative inline-flex">
          <button
            type="button"
            onClick={() => setLocateRequest((value) => value + 1)}
            aria-label="현재 위치로 이동"
            title="현재 위치로 이동"
            className="map-icon-button border-border/60 bg-surface/55 shadow-sm backdrop-blur hover:bg-surface/80"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="6.5" />
              <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none" />
              <path d="M12 2.75v3M12 18.25v3M2.75 12h3M18.25 12h3" />
            </svg>
          </button>
          <IconTooltip>현재위치로 이동</IconTooltip>
        </span>
        {user ? (
          <span className="group relative inline-flex">
            <button
              type="button"
              aria-label="집으로 이동"
              title="집으로 이동"
              disabled={!hasHomeLocation}
              onClick={() => {
                if (!hasHomeLocation) {
                  flash('로그인 후 마이페이지에서 집 주소를 저장해주세요.');
                  return;
                }
                setHomeRequest((value) => value + 1);
              }}
              className="map-icon-button border-border/60 bg-surface/55 shadow-sm backdrop-blur hover:bg-surface/80 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-surface/55"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 10.75 12 4l8 6.75" />
                <path d="M6.5 9.75V20h11V9.75" />
                <path d="M10 20v-5.5h4V20" />
              </svg>
            </button>
            <IconTooltip>집으로 이동</IconTooltip>
          </span>
        ) : null}
        {user ? (
          <span className="group relative inline-flex">
            <button
              type="button"
              aria-label="대학으로 이동"
              title="대학으로 이동"
              disabled={!hasSchoolLocation}
              onClick={() => {
                if (!hasSchoolLocation) {
                  flash('마이페이지에서 대학을 저장해주세요.');
                  return;
                }
                setSchoolRequest((value) => value + 1);
              }}
              className="map-icon-button border-border/60 bg-surface/55 shadow-sm backdrop-blur hover:bg-surface/80 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-surface/55"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 9.5 12 5l9 4.5-9 4.5-9-4.5Z" />
                <path d="M7 11.5v4.25c0 1.2 2.24 2.25 5 2.25s5-1.05 5-2.25V11.5" />
                <path d="M21 9.5v5" />
              </svg>
            </button>
            <IconTooltip>대학으로 이동</IconTooltip>
          </span>
        ) : null}
        {user ? (
          <span className="group relative inline-flex">
            <button
              type="button"
              aria-label={showHomeMarker ? '집 마커 숨기기' : '집 마커 표시'}
              title={showHomeMarker ? '집 마커 숨기기' : '집 마커 표시'}
              disabled={!hasHomeLocation}
              onClick={() => {
                if (!hasHomeLocation) {
                  flash('로그인 후 마이페이지에서 집 주소를 저장해주세요.');
                  return;
                }
                setShowHomeMarker((value) => !value);
              }}
              className={`map-icon-button ${showHomeMarker ? 'map-icon-button--home-visible' : 'map-icon-button--home-hidden'} disabled:cursor-not-allowed disabled:opacity-40`}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 21s6-5.1 6-10a6 6 0 0 0-12 0c0 4.9 6 10 6 10Z" />
                <path d="M9.5 11.1 12 8.8l2.5 2.3" />
                <path d="M10.4 10.7v3.2h3.2v-3.2" />
                {!showHomeMarker ? <path d="M4.5 4.5 19.5 19.5" /> : null}
              </svg>
            </button>
            <IconTooltip>{showHomeMarker ? '집 마커 숨기기' : '집 마커 표시'}</IconTooltip>
          </span>
        ) : null}
      </div>

      {heatmapEnabled ? (
        <div className="absolute bottom-16 left-1/2 z-[440] flex -translate-x-1/2 items-center gap-3 rounded-card border border-border bg-surface/95 px-4 py-2 text-[13px] font-semibold text-text shadow-lg backdrop-blur">
          <span>낮음</span>
          <div className="flex h-3 w-[180px] overflow-hidden rounded-full border border-border/50" aria-label="히트맵 5단계 범례">
            {HEATMAP_COLORS_ORDERED.map((color, index) => (
              <span key={`${color}-${index}`} className="h-full flex-1" style={{ backgroundColor: color }} />
            ))}
          </div>
          <span>높음</span>
          <strong className="text-[var(--color-heatmap-5)]">{HEAT_LAYERS.find((layer) => layer.key === heatLayer)?.label}</strong>
        </div>
      ) : null}

      {scoresLoading ? <StatusPill>지도 데이터를 불러오는 중입니다.</StatusPill> : null}
      {scoresError ? <StatusPill tone="danger">지도 데이터를 불러오지 못했습니다.</StatusPill> : null}
      {amenitiesQuery.isFetching ? <StatusPill>시설 데이터를 불러오는 중입니다.</StatusPill> : null}
      {medicalFacilitiesFetching ? <StatusPill>의료 데이터를 불러오는 중입니다.</StatusPill> : null}
      {toast ? <StatusPill position="top-[88px]" tone="dark">{toast}</StatusPill> : null}

      <MapPopup
        popup={popup}
        onClose={() => {
          setPopup(null);
        }}
        heatLayer={heatLayer}
        ranks={ranks}
        rankTotal={scoresData.length}
        onRegionDashboardOpen={openRegionDashboard}
        onRegionCandidateAdd={addRegionCandidate}
      />
    </main>
  );
}

function StatusPill({ children, tone = 'dark', position = 'top-5' }: { children: React.ReactNode; tone?: 'dark' | 'danger'; position?: string }) {
  return (
    <div className={`absolute left-1/2 z-[560] -translate-x-1/2 rounded-[8px] px-4 py-2 text-[13px] font-semibold shadow-lg ${position} ${tone === 'danger' ? 'bg-danger text-white' : 'bg-[var(--map-status-bg)] text-white'}`}>
      {children}
    </div>
  );
}
