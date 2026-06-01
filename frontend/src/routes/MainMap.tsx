import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';

import AmenityLayer from '@/components/Map/AmenityLayer';
import HeatMap from '@/components/Map/HeatMap';
import type { ScoreLayerKey } from '@/components/Map/HeatMap';
import ThemeToggle from '@/components/ThemeToggle';
import TransactionPinLayer from '@/components/Map/TransactionPinLayer';
import {
  ChoiceList,
  DropdownButton,
  FilterButton,
  IconTooltip,
  ModeGuide,
  RangePanel,
  ResetButton,
  SegmentButton,
} from '@/components/Map/MapControls';
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
} from '@/components/Map/MapInteractionLayers';
import type { SelectedPlacePin } from '@/components/Map/MapInteractionLayers';
import MapPopup, { buildScoreRanks, type SelectedPopup } from '@/components/Map/MapPopup';
import MedicalControlPanel, { type MedicalCategory } from '@/components/Map/MedicalControlPanel';
import RealEstateHelperPanel from '@/components/Map/RealEstateHelperPanel';
import type { MapState, RentDealMapPin } from '@/components/Map/TransactionPinLayer';
import { useAuth } from '@/contexts/AuthContext';
import { useAdongMatchCounts } from '@/hooks/useAdongMatchCounts';
import { useAdongScores, useLdongScores } from '@/hooks/useAdongs';
import { useRentDealCache } from '@/hooks/useRentDealCache';
import { useStudioMatchFilters } from '@/hooks/useStudioMatchFilters';
import { getAmenitiesBbox, getDashboardLdongAtPoint, getMapSearch, getMedicalFacilities, getMedicalSpecialtyGroups, getRentDealDetail } from '@/lib/api';
import { setDashboardMiniMapTransitionTarget } from '@/lib/dashboardTransition';
import { HEATMAP_COLORS_ORDERED } from '@/lib/colors';
import { getSavedMapView, saveMapView } from '@/lib/mapViewMemory';
import { DEFAULT_WEIGHTS } from '@/types/api';
import type {
  ExploreDealType,
  ExplorePeriod,
  MapSearchItem,
} from '@/types/api';

import 'leaflet/dist/leaflet.css';

type MapMode = 'plain' | 'heatmap' | 'realestate' | 'facility' | 'medical';
type RegionLevel = 'adong' | 'ldong';

function ActiveModeGuide({ mapMode, regionLevel }: { mapMode: MapMode; regionLevel: RegionLevel }) {
  if (mapMode === 'plain') {
    return (
      <ModeGuide title={'\uc9c0\ub3c4'}>
        {'\uac80\uc0c9 \uacb0\uacfc, \ud604\uc7ac \uc704\uce58, \uc9d1 \uc704\uce58, \uc9c0\ub3c4 \ud074\ub9ad \uc9c0\uc810\uc744 \uae30\uc900\uc73c\ub85c \uc9c0\ub3c4\ub97c \ud0d0\uc0c9\ud569\ub2c8\ub2e4.'}
      </ModeGuide>
    );
  }
  if (mapMode === 'heatmap') {
    return (
      <ModeGuide title={'\ud788\ud2b8\ub9f5'}>
        {'\uc120\ud0dd\ud55c \uc810\uc218\uc758 '}
        {regionLevel === 'adong' ? '\ud589\uc815\ub3d9\ubcc4' : '\ubc95\uc815\ub3d9\ubcc4'}
        {' \ubd84\ud3ec\ub97c \uc0c9\uc73c\ub85c \ube44\uad50\ud569\ub2c8\ub2e4. i\ub97c \uc62c\ub9ac\uba74 \uacc4\uc0b0 \uae30\uc900\uc744 \ubcfc \uc218 \uc788\uc2b5\ub2c8\ub2e4.'}
      </ModeGuide>
    );
  }
  if (mapMode === 'realestate') {
    return (
      <ModeGuide title={'\ubd80\ub3d9\uc0b0'}>
        {'\uae30\uac04, \uc720\ud615, \ubcf4\uc99d\uae08, \uc6d4\uc138, \uba74\uc801 \uc870\uac74\uc5d0 \ub9de\ub294 \uc2e4\uac70\ub798\ub97c \uc9c0\ub3c4\uc5d0 \ud45c\uc2dc\ud569\ub2c8\ub2e4. \ud655\ub300\ud558\uba74 \ub354 \uc791\uc740 \ubc94\uc704\ub85c \ubb36\uc785\ub2c8\ub2e4.'}
      </ModeGuide>
    );
  }
  if (mapMode === 'facility') {
    return (
      <ModeGuide title={'\uc2dc\uc124'}>
        {'\uc120\ud0dd\ud55c \uc0dd\ud65c\uc2dc\uc124\uc744 \uc9c0\ub3c4\uc5d0 \ud45c\uc2dc\ud569\ub2c8\ub2e4. \ud45c\uc2dc\ud560 \uc2dc\uc124\uc774 \uc5c6\uc73c\uba74 \uc544\ubb34 \uac83\ub3c4 \uc120\ud0dd\ud558\uc9c0 \uc54a\uc740 \uc0c1\ud0dc\uc785\ub2c8\ub2e4.'}
      </ModeGuide>
    );
  }
  return (
    <ModeGuide title={'\uc758\ub8cc'}>
      {'\uc120\ud0dd\ud55c \ubcd1\uc6d0, \uce58\uacfc, \uc57d\uad6d, \uc751\uae09\uc2e4\uc744 \uc9c0\ub3c4\uc5d0 \ud45c\uc2dc\ud569\ub2c8\ub2e4. \uc9c0\uae08 \ubb38 \uc5f0 \uacf3\uc744 \ucf1c\uba74 \uc800\uc7a5\ub41c \uc6b4\uc601\uc2dc\uac04 \uae30\uc900\uc73c\ub85c \ud544\ud130\ub9c1\ud569\ub2c8\ub2e4.'}
    </ModeGuide>
  );
}

type FacilityKey =
  | 'subway_station'
  | 'bus_stop'
  | 'park'
  | 'library'
  | 'convenience'
  | 'mart'
  | 'daiso'
  | 'restaurant'
  | 'cafe'
  | 'nightlife'
  | 'laundry'
  | 'beauty'
  | 'oliveyoung'
  | 'gym'
  | 'book_stationery'
  | 'study_cafe';

interface AiMapTarget {
  label: string;
  lat: number;
  lng: number;
}

interface FacilityLookupBbox {
  lng1: number;
  lat1: number;
  lng2: number;
  lat2: number;
  source: 'map' | 'nearby';
}

const SEOUL_AI_TARGET_BOUNDS = {
  minLat: 37.35,
  maxLat: 37.75,
  minLng: 126.7,
  maxLng: 127.3,
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

const HOME_MARKER_VISIBILITY_STORAGE_KEY = 'map.homeMarker.visible';
const HEAT_LAYERS: Array<{ key: ScoreLayerKey; label: string }> = [
  { key: 'composite', label: '종합 점수' },
  { key: 'rent', label: '부동산 점수' },
  { key: 'transit', label: '교통 점수' },
  { key: 'amenity', label: '편의시설 점수' },
  { key: 'safety', label: '안전 지수' },
];

const HEAT_LAYER_DESCRIPTIONS: Record<ScoreLayerKey, string> = {
  composite: '기본 가중치 33/33/34로 부동산·편의시설·교통 점수를 합산한 값입니다.',
  rent: '\ucd5c\uadfc 365\uc77c \uc2e4\uac70\ub798 \uae30\uc900\uc785\ub2c8\ub2e4.\n(\uc6d4\uc138 + \ubcf4\uc99d\uae08\u00d70.005) / \uba74\uc801(m\u00b2)\uc744 \uacc4\uc0b0\ud569\ub2c8\ub2e4.\n\uc0c1\ud558\uc704 5%\ub97c \uc904\uc778 \ud3c9\uade0\uc744 \uc0ac\uc6a9\ud558\uace0, \uac12\uc774 \ub0ae\uc744\uc218\ub85d \ub192\uc740 \uc810\uc218\uc785\ub2c8\ub2e4.',
  transit: '가장 가까운 지하철역 거리 점수 60%와 면적당 버스정류장 밀도 점수 40%를 합산합니다. 지하철 거리는 1km를 기준으로 멀수록 낮아집니다.',
  amenity: '면적당 생활시설 밀도 60.9%, 의료시설 밀도 10.8%, 공원 면적 비율 28.3%를 합산합니다. 생활/의료 밀도는 로그 정규화합니다.',
  safety: '교통사고, 화재, 범죄, 생활안전, 자살, 감염병 6개 지역안전등급을 평균한 구 단위 지표입니다. 등급이 낮을수록 안전한 원자료를 0~100 점수로 변환해 표시합니다.',
};

const DEAL_TYPE_LABELS: Record<ExploreDealType, string> = {
  yeonlip: '연립',
  dasedae: '다세대',
  yeonlip_dasedae: '연립다세대',
  dagagu: '다가구',
  danok: '단독',
  danok_dagagu: '단독다가구',
  officetel: '오피스텔',
  apt: '아파트',
};

const DEAL_TYPE_FILTER_OPTIONS: ExploreDealType[] = ['yeonlip', 'dasedae', 'dagagu', 'danok', 'officetel', 'apt'];

const PERIOD_LABELS: Record<ExplorePeriod, string> = {
  '3m': '최근 3개월',
  '6m': '최근 6개월',
  '12m': '최근 1년',
  '24m': '최근 2년',
  all: '전체 기간',
};

const FACILITY_LABELS: Record<FacilityKey, string> = {
  subway_station: '지하철역',
  bus_stop: '버스정류장',
  park: '공원',
  library: '도서관',
  convenience: '편의점',
  mart: '슈퍼마켓',
  daiso: '다이소',
  restaurant: '음식점',
  cafe: '카페',
  nightlife: '주점',
  laundry: '세탁',
  beauty: '미용',
  oliveyoung: '올리브영',
  gym: '헬스장',
  book_stationery: '서점/문구',
  study_cafe: '스터디카페',
};

const FACILITY_ORDER: FacilityKey[] = [
  'subway_station',
  'bus_stop',
  'park',
  'library',
  'convenience',
  'mart',
  'daiso',
  'restaurant',
  'cafe',
  'nightlife',
  'laundry',
  'beauty',
  'oliveyoung',
  'gym',
  'book_stationery',
  'study_cafe',
];

const MEDICAL_CATEGORY_ORDER: MedicalCategory[] = ['hospital', 'dental', 'pharmacy', 'emergency'];

const FACILITY_ICONS: Record<FacilityKey, string> = {
  subway_station: '🚇',
  bus_stop: '🚌',
  park: '🌳',
  library: '📚',
  convenience: '🏪',
  mart: '🛒',
  daiso: '<span style="color:#dc2626;font-size:14px;line-height:1">■</span>',
  restaurant: '🍜',
  cafe: '☕',
  nightlife: '🍺',
  laundry: '🧺',
  beauty: '✂',
  oliveyoung: '🫒',
  gym: '🏋',
  book_stationery: '✏',
  study_cafe: '📖',
};

const RANGE_ALL = {
  deposit: { min: 0, max: 999_999 },
  monthly: { min: 0, max: 9_999 },
  converted: { min: 0, max: 9_999 },
  area: { min: 0, max: 10_000 },
};

function formatRangeLabel(label: string, min: number, max: number, allMax: number, unit = '') {
  if (min <= 0 && max >= allMax) return `${label} 전체`;
  return `${label} ${min.toLocaleString()}-${max.toLocaleString()}${unit}`;
}

function formatDealTypes(types: ExploreDealType[]) {
  if (types.length >= 5) return '전체 유형';
  return types.map((t) => DEAL_TYPE_LABELS[t]).join(', ');
}

export default function MainMap() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const [regionLevel, setRegionLevel] = useState<RegionLevel>('adong');
  const [mapMode, setMapMode] = useState<MapMode>(() => {
    const mode = searchParams.get('mode');
    return mode === 'plain' || mode === 'heatmap' || mode === 'realestate' || mode === 'facility' || mode === 'medical' ? mode : 'heatmap';
  });
  const [heatLayer, setHeatLayer] = useState<ScoreLayerKey>('composite');
  const [facilityKeys, setFacilityKeys] = useState<Set<FacilityKey>>(
    () => new Set(),
  );
  const [medicalCategories, setMedicalCategories] = useState<Set<MedicalCategory>>(
    () => new Set(),
  );
  const [medicalSpecialtyGroups, setMedicalSpecialtyGroups] = useState<Set<string>>(
    () => new Set(),
  );
  const [medicalOpenNow, setMedicalOpenNow] = useState(false);
  const [mapState, setMapState] = useState<MapState | null>(null);
  const savedMapView = useMemo(() => getSavedMapView(), []);
  const [popup, setPopup] = useState<SelectedPopup>(null);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<MapSearchItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedSearchItem, setSelectedSearchItem] = useState<MapSearchItem | null>(null);
  const [selectedPlacePin, setSelectedPlacePin] = useState<SelectedPlacePin | null>(null);
  const [nearbyFacilityBbox, setNearbyFacilityBbox] = useState<FacilityLookupBbox | null>(null);
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
  const [routeTransition, setRouteTransition] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [realEstateHelperOpen, setRealEstateHelperOpen] = useState(false);
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
  const mapModeRef = useRef(mapMode);
  const mapStateRef = useRef<MapState | null>(null);

  const { filters, patch, reset } = useStudioMatchFilters();

  useEffect(() => {
    mapModeRef.current = mapMode;
  }, [mapMode]);
  const adongScoresQuery = useAdongScores(DEFAULT_WEIGHTS);
  const ldongScoresQuery = useLdongScores(DEFAULT_WEIGHTS);
  const scoresData = regionLevel === 'ldong' ? (ldongScoresQuery.data ?? []) : (adongScoresQuery.data ?? []);
  const scoresLoading = regionLevel === 'ldong' ? ldongScoresQuery.isLoading : adongScoresQuery.isLoading;
  const scoresError = regionLevel === 'ldong' ? ldongScoresQuery.isError : adongScoresQuery.isError;
  const matchQuery = useAdongMatchCounts(filters, mapMode === 'realestate');
  const matchCounts = matchQuery.data?.adongs ?? [];

  const rentCacheQuery = useRentDealCache(mapMode === 'realestate', filters, mapState);
  const filteredPins = rentCacheQuery.pins;

  const selectedFacilityCategories = useMemo(() => Array.from(facilityKeys), [facilityKeys]);
  const activeFacilityBbox = useMemo<FacilityLookupBbox | null>(() => {
    if (nearbyFacilityBbox) return nearbyFacilityBbox;
    if (!mapState?.bbox) return null;
    return { ...mapState.bbox, source: 'map' };
  }, [mapState?.bbox, nearbyFacilityBbox]);
  const amenitiesQuery = useQuery({
    queryKey: [
      'amenities',
      'bbox',
      activeFacilityBbox?.source,
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
      limit: 800,
    }),
    enabled: mapMode === 'facility' && activeFacilityBbox != null && selectedFacilityCategories.length > 0,
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
    enabled: mapMode === 'medical',
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
        limit: 800,
      }),
      enabled: mapMode === 'medical' && medicalBbox != null,
      staleTime: 60_000,
    })),
  });
  const medicalFacilitiesFetching = medicalFacilitiesQueries.some((query) => query.isFetching);
  const visibleMedicalFacilities = (() => {
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
  })();

  const ranks = useMemo(() => buildScoreRanks(scoresData), [scoresData]);

  const selectedJibun = popup?.type === 'deal' ? popup.key : null;
  const heatmapActiveLayer: ScoreLayerKey = heatLayer;
  const heatmapMode = 'score';
  const heatmapVisible = mapMode === 'heatmap';
  const showRealEstatePins = mapMode === 'realestate';
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

  const flash = (message: string) => {
    setToast(message);
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => {
      setToast(null);
      toastTimer.current = null;
    }, 2200);
  };

  useEffect(() => () => {
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(HOME_MARKER_VISIBILITY_STORAGE_KEY, showHomeMarker ? 'true' : 'false');
    } catch {
      // Ignore storage failures; marker toggle still works for current session.
    }
  }, [showHomeMarker]);

  useEffect(() => {
    setNearbyFacilityBbox(null);
  }, [selectedPlacePin?.lat, selectedPlacePin?.lng]);

  const handleModeChange = (mode: MapMode) => {
    setMapMode(mode);
    setPopup(null);
    setNearbyFacilityBbox(null);
    setActiveAiMapTarget(null);
    setOpenDropdown(null);
    setRealEstateHelperOpen(false);
    const next = new URLSearchParams(searchParams);
    if (mode === 'heatmap') next.delete('mode');
    else next.set('mode', mode);
    setSearchParams(next, { replace: true });
  };

  const toggleDropdown = (id: string) => {
    setRealEstateHelperOpen(false);
    setOpenDropdown((prev) => (prev === id ? null : id));
  };

  const handlePinClick = (key: string, pin: RentDealMapPin) => {
    if ('kind' in pin) return;
    setPopup({ type: 'deal_loading', key });
    getRentDealDetail(pin.id)
      .then((deal) => setPopup({ type: 'deal', key, pins: [deal] }))
      .catch(() => {
        setPopup(null);
        flash('거래 상세 정보를 불러오지 못했습니다.');
      });
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

  const persistMapView = useCallback((state?: MapState | null) => {
    const targetState = state ?? mapStateRef.current;
    if (!targetState?.bbox || typeof targetState.zoom !== 'number') return;
    saveMapView({
      center: [
        (targetState.bbox.lat1 + targetState.bbox.lat2) / 2,
        (targetState.bbox.lng1 + targetState.bbox.lng2) / 2,
      ],
      zoom: targetState.zoom,
      mode: mapModeRef.current,
    });
  }, []);

  const handleMapStateChange = useCallback((state: MapState) => {
    mapStateRef.current = state;
    setMapState(state);
    persistMapView(state);
  }, [persistMapView]);

  const handleDashboardOpen = async () => {
    persistMapView();
    const selectedTarget = selectedPlacePin ?? activeAiMapTarget;
    const centerTarget = mapState?.bbox
      ? {
        lat: (mapState.bbox.lat1 + mapState.bbox.lat2) / 2,
        lng: (mapState.bbox.lng1 + mapState.bbox.lng2) / 2,
      }
      : null;
    const target = selectedTarget ?? centerTarget;
    setDashboardMiniMapTransitionTarget();
    setRouteTransition(true);
    let dashboardPath = '/dashboard?region_type=ldong';
    if (target) {
      try {
        const ldong = await getDashboardLdongAtPoint(target.lat, target.lng);
        if (ldong.slug) {
          dashboardPath = `/dashboard?region_type=ldong&slug=${encodeURIComponent(ldong.slug)}`;
        }
      } catch {
        flash('현재 위치의 법정동을 찾지 못해 기본 대시보드로 이동합니다.');
      }
    }
    window.setTimeout(() => navigate(dashboardPath), 360);
  };

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
      if (openDropdown) {
        setOpenDropdown(null);
        handled = true;
      }
      if (realEstateHelperOpen) {
        setRealEstateHelperOpen(false);
        handled = true;
      }
      if (handled) event.preventDefault();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [popup, searchResults.length, searchLoading, openDropdown, realEstateHelperOpen]);

  useEffect(() => {
    const hasAiParams = searchParams.has('ai_lat') || searchParams.has('ai_lng') || searchParams.has('ai_label');
    if (!hasAiParams) return;
    if (aiMapTarget) {
      setActiveAiMapTarget(aiMapTarget);
    } else {
      setActiveAiMapTarget(null);
    }
    const next = new URLSearchParams(searchParams);
    next.delete('ai_lat');
    next.delete('ai_lng');
    next.delete('ai_label');
    setSearchParams(next, { replace: true });
  }, [aiMapTarget, searchParams, setSearchParams]);

  return (
    <main className="map-redesign relative h-screen w-screen overflow-hidden bg-bg text-text">
      <h1 className="sr-only">서울 주거 지도</h1>

      <HeatMap
        adongs={scoresData}
        activeLayer={heatmapActiveLayer}
        heatmapVisible={heatmapVisible}
        mode={heatmapMode}
        matchCounts={matchCounts}
        regionLevel={regionLevel}
        initialCenter={savedMapView?.center}
        initialZoom={savedMapView?.zoom}
        onAdongClick={mapMode === 'heatmap' ? (adong) => setPopup({ type: 'adong', adong }) : undefined}
      >
        <CurrentLocationLayer
          requestId={locateRequest}
          onError={(message) => flash(message)}
          onLocated={(lat, lng) => {
            setSelectedSearchItem(null);
            setPopup(null);
            setSelectedPlacePin({ lat, lng, label: '\ud604\uc7ac \uc704\uce58', source: 'current-location' });
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
            setSelectedPlacePin({ lat, lng, label: '\uc9d1', source: 'home' });
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
          enabled={mapMode === 'plain' || mapMode === 'facility' || mapMode === 'realestate' || mapMode === 'medical'}
          onSelect={(pin) => {
            setSelectedSearchItem(null);
            setPopup(null);
            setSelectedPlacePin(pin);
          }}
        />
        {mapMode !== 'heatmap' ? <SelectedPlacePinLayer pin={selectedPlacePin} /> : null}
        <AiMapTargetLayer target={activeAiMapTarget} />
        {mapMode !== 'heatmap' && showHomeMarker ? (
          <HomeMarker
            lat={user?.home_lat}
            lng={user?.home_lng}
            onClick={() => setPopup({ type: 'home', address: user?.address })}
          />
        ) : null}
        {showRealEstatePins ? (
          <TransactionPinLayer
            pins={filteredPins}
            selectedJibun={selectedJibun}
            onPinClick={handlePinClick}
            onMapStateChange={handleMapStateChange}
            suppressTooltips={popup != null}
          />
        ) : (
          <MapStateProbe onMapStateChange={handleMapStateChange} />
        )}
        {mapMode === 'facility' ? (
          <AmenityLayer
            items={visibleAmenities}
            getIcon={(category) => FACILITY_ICONS[category as FacilityKey] ?? '•'}
            onSelect={(item) => setPopup({
              type: 'facility',
              title: item.name,
              description: FACILITY_LABELS[item.category as FacilityKey] ?? item.category,
            })}
          />
        ) : null}
        {mapMode === 'medical' ? (
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
        ) : null}
      </HeatMap>

      <section className="pointer-events-none absolute left-5 top-5 z-[500] grid justify-items-start gap-2" aria-label="지도 검색과 필터">
        <div className="pointer-events-auto relative">
          <label className="flex h-11 w-[430px] items-center gap-3 rounded-card border border-border bg-surface/95 px-3 shadow-lg backdrop-blur">
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center text-[18px] font-semibold text-text-muted" aria-hidden="true">⌕</span>
            <input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchResults[0]) {
                  if (hasValidCoordinate(searchResults[0])) {
                    const item = searchResults[0];
                    setSelectedSearchItem(item);
                    setSelectedPlacePin({ lat: item.lat, lng: item.lng, label: item.name, source: 'search' });
                    setPopup({ type: 'search', item });
                  } else {
                    flash('좌표가 없는 검색 결과입니다.');
                  }
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
            <div className="absolute left-0 top-[calc(100%+6px)] z-[650] w-[430px] overflow-hidden rounded-card border border-border bg-surface/95 shadow-xl backdrop-blur">
              {searchLoading ? <div className="px-3 py-2 text-[13px] font-semibold text-text-muted">검색 중...</div> : null}
              {searchResults.map((item) => (
                <button key={item.id} type="button" onClick={() => { if (!hasValidCoordinate(item)) { flash('좌표가 없는 검색 결과입니다.'); return; } setSelectedSearchItem(item); setSelectedPlacePin({ lat: item.lat, lng: item.lng, label: item.name, source: 'search' }); setPopup({ type: 'search', item }); setSearchText(item.name); setSearchResults([]); }} className="block w-full border-t border-border/70 px-3 py-2 text-left transition first:border-t-0 hover:bg-[var(--color-heatmap-1)]">
                  <span className="block text-[13px] font-semibold text-text">{item.name}</span>
                  <span className="mt-0.5 block truncate text-[12px] text-text-muted">{item.label}{item.address ? ' · ' + item.address : ''}</span>
                </button>
              ))}
            </div>
          ) : null}
          <div className="pointer-events-auto absolute left-[calc(100%+8px)] top-0">
            <ActiveModeGuide mapMode={mapMode} regionLevel={regionLevel} />
          </div>
        </div>

        <div className="pointer-events-auto grid w-[var(--map-control-width)] grid-cols-5 rounded-card border border-border bg-surface/95 p-1 shadow-lg backdrop-blur" role="group" aria-label="지도 모드">
          <SegmentButton active={mapMode === 'plain'} onClick={() => handleModeChange('plain')}>지도</SegmentButton>
          <SegmentButton active={mapMode === 'heatmap'} onClick={() => handleModeChange('heatmap')}>히트맵</SegmentButton>
          <SegmentButton active={mapMode === 'realestate'} onClick={() => handleModeChange('realestate')}>부동산</SegmentButton>
          <SegmentButton active={mapMode === 'facility'} onClick={() => handleModeChange('facility')}>시설</SegmentButton>
          <SegmentButton active={mapMode === 'medical'} onClick={() => handleModeChange('medical')}>{'\uc758\ub8cc'}</SegmentButton>
        </div>


        {mapMode === 'heatmap' ? (
          <div className="pointer-events-auto relative z-[600] w-[152px] rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur">
            <div className="mb-2 grid w-full grid-cols-2 rounded-[12px] border border-[var(--color-heatmap-2)] bg-surface/80 p-1" role="group" aria-label="지역 단위">
              <button type="button" onClick={() => setRegionLevel('adong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'adong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>행정동</button>
              <button type="button" onClick={() => setRegionLevel('ldong')} className={`h-8 rounded-[9px] px-3 text-[13px] font-semibold transition ${regionLevel === 'ldong' ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)] shadow-sm' : 'text-text-muted hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}>법정동</button>
            </div>
            <div className="grid w-full gap-1.5">
              {HEAT_LAYERS.map((layer) => (
                <div key={layer.key} className="group relative">
                  <button
                    type="button"
                    onClick={() => {
                      setHeatLayer(layer.key);
                    }}
                    className={`relative flex h-9 w-full items-center rounded-[var(--map-control-radius)] border px-3 pr-7 text-left text-[13px] font-semibold shadow-sm transition ${
                      heatLayer === layer.key
                        ? 'border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]'
                        : 'border-border bg-surface/95 text-text hover:bg-[var(--color-heatmap-1)]'
                    }`}
                  >
                    <span>{layer.label}</span>
                    <span
                      aria-label={`${layer.label} 계산 방식`}
                      className="absolute right-1.5 top-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full border border-border/80 bg-surface/70 text-[9px] font-bold leading-none text-text-subtle"
                    >
                      i
                    </span>
                  </button>
                  <div className="pointer-events-none absolute left-[calc(100%+8px)] top-0 z-[700] hidden w-[300px] whitespace-pre-line rounded-card border border-[var(--color-heatmap-2)] bg-surface p-3 text-[12px] leading-5 text-text shadow-xl group-hover:block">
                    <strong className="mb-1 block text-[13px] text-[var(--color-heatmap-5)]">{layer.label}</strong>
                    {HEAT_LAYER_DESCRIPTIONS[layer.key]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {mapMode === 'realestate' ? (
          <div className="pointer-events-none flex items-start gap-2">
            <div className="pointer-events-auto relative z-[600] grid w-[152px] min-w-[152px] max-w-[152px] gap-2 rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur">
            <div className="grid grid-cols-2 gap-1 rounded-[var(--map-control-radius)] border border-border bg-surface-alt p-1">
              <button
                type="button"
                onClick={() => patch({ filter_mode: 'converted' })}
                className={`h-8 rounded-[6px] text-[12px] font-semibold ${filters.filter_mode === 'converted' ? 'bg-surface text-text shadow-sm' : 'text-text-muted'}`}
              >
                환산
              </button>
              <button
                type="button"
                onClick={() => patch({ filter_mode: 'raw' })}
                className={`h-8 rounded-[6px] text-[12px] font-semibold ${filters.filter_mode === 'raw' ? 'bg-surface text-text shadow-sm' : 'text-text-muted'}`}
              >
                보증/월세
              </button>
            </div>
            <DropdownButton id="period" label={PERIOD_LABELS[filters.period]} active width="w-full" open={openDropdown === 'period'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <ChoiceList
                selected={filters.period}
                onSelect={(value) => { patch({ period: value as ExplorePeriod }); setOpenDropdown(null); }}
                items={Object.entries(PERIOD_LABELS).map(([value, label]) => ({ value, label }))}
              />
            </DropdownButton>
            <DropdownButton id="deal-type" label={formatDealTypes(filters.deal_types)} active width="w-full max-w-full" open={openDropdown === 'deal-type'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <div className="grid gap-2">
                <h3 className="m-0 pr-8 text-[14px] font-semibold text-text">유형 선택</h3>
                <div className="flex flex-wrap gap-1.5">
                {DEAL_TYPE_FILTER_OPTIONS.map((type) => {
                  const active = filters.deal_types.includes(type);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        const next = active
                          ? filters.deal_types.filter((t) => t !== type)
                          : [...filters.deal_types, type];
                        patch({ deal_types: next.length > 0 ? next : [type] });
                      }}
                      className={`h-8 rounded-[6px] px-2 text-[12px] font-semibold transition ${active ? 'bg-[var(--color-heatmap-1)] text-[var(--color-heatmap-5)]' : 'bg-surface-alt text-text hover:bg-[var(--color-heatmap-1)] hover:text-[var(--color-heatmap-5)]'}`}
                    >
                      {DEAL_TYPE_LABELS[type]}
                    </button>
                  );
                })}
                </div>
              </div>
            </DropdownButton>
            <DropdownButton id="deposit" label={formatRangeLabel('보증금', filters.deposit_min, filters.deposit_max, RANGE_ALL.deposit.max)} width="w-full" open={openDropdown === 'deposit'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'converted'}>
              <RangePanel
                title="보증금 범위"
                unit="만원"
                min={filters.deposit_min}
                max={filters.deposit_max}
                onChange={(deposit_min, deposit_max) => patch({ deposit_min, deposit_max })}
                step={100}
                presets={[{ label: '전체', min: RANGE_ALL.deposit.min, max: RANGE_ALL.deposit.max }, { label: '3천 이하', min: 0, max: 3000 }, { label: '5천 이하', min: 0, max: 5000 }, { label: '1억 이하', min: 0, max: 10000 }]}
              />
            </DropdownButton>
            <DropdownButton id="monthly" label={formatRangeLabel('월세', filters.monthly_min, filters.monthly_max, RANGE_ALL.monthly.max)} width="w-full" open={openDropdown === 'monthly'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'converted'}>
              <RangePanel
                title="월세 범위"
                unit="만원"
                min={filters.monthly_min}
                max={filters.monthly_max}
                onChange={(monthly_min, monthly_max) => patch({ monthly_min, monthly_max })}
                step={5}
                presets={[{ label: '전체', min: RANGE_ALL.monthly.min, max: RANGE_ALL.monthly.max }, { label: '50 이하', min: 0, max: 50 }, { label: '80 이하', min: 0, max: 80 }, { label: '120 이하', min: 0, max: 120 }]}
              />
            </DropdownButton>
            <DropdownButton id="converted" label={formatRangeLabel('환산월세', filters.converted_min, filters.converted_max, RANGE_ALL.converted.max)} width="w-full" open={openDropdown === 'converted'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)} disabled={filters.filter_mode === 'raw'}>
              <RangePanel
                title="환산월세 범위"
                unit="만원"
                min={filters.converted_min}
                max={filters.converted_max}
                onChange={(converted_min, converted_max) => patch({ converted_min, converted_max })}
                step={5}
                presets={[{ label: '전체', min: RANGE_ALL.converted.min, max: RANGE_ALL.converted.max }, { label: '60 이하', min: 0, max: 60 }, { label: '100 이하', min: 0, max: 100 }, { label: '150 이하', min: 0, max: 150 }]}
              />
            </DropdownButton>
            <DropdownButton id="area" label={formatRangeLabel('면적', filters.area_min, filters.area_max, RANGE_ALL.area.max, 'm²')} width="w-full" open={openDropdown === 'area'} onToggle={toggleDropdown} onClose={() => setOpenDropdown(null)}>
              <RangePanel
                title="면적 범위"
                unit="m²"
                min={filters.area_min}
                max={filters.area_max}
                onChange={(area_min, area_max) => patch({ area_min, area_max })}
                presets={[{ label: '전체', min: RANGE_ALL.area.min, max: RANGE_ALL.area.max }, { label: '10-20m²', min: 10, max: 20 }, { label: '20-40m²', min: 20, max: 40 }, { label: '40-60m²', min: 40, max: 60 }]}
              />
            </DropdownButton>
            <ResetButton onClick={reset}>초기화</ResetButton>
            </div>
            <RealEstateHelperPanel open={realEstateHelperOpen} onToggle={() => { setOpenDropdown(null); setRealEstateHelperOpen((prev) => !prev); }} />
          </div>
        ) : null}

        {mapMode === 'facility' ? (
          <div className="pointer-events-auto relative z-[600] grid w-[152px] justify-items-start gap-1 overflow-visible rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur">
            {nearbyFacilityBbox ? (
              <button
                type="button"
                onClick={() => setNearbyFacilityBbox(null)}
                className="h-8 w-full rounded-[var(--map-control-radius)] border border-[var(--color-heatmap-2)] bg-[var(--color-heatmap-1)] px-2 text-[12px] font-semibold text-[var(--color-heatmap-5)] transition hover:bg-[var(--color-heatmap-2)]/70"
              >
                {'\uc9c0\ub3c4 \ubc94\uc704\ub85c \ubcf4\uae30'}
              </button>
            ) : null}
            {FACILITY_ORDER.map((key) => (
              <FilterButton key={key} active={facilityKeys.has(key)} onClick={() => toggleFacility(key)} className="w-full">
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden="true" className="inline-flex h-4 w-4 items-center justify-center" dangerouslySetInnerHTML={{ __html: FACILITY_ICONS[key] }} />
                  <span>{FACILITY_LABELS[key]}</span>
                </span>
              </FilterButton>
            ))}
            <ResetButton onClick={() => { setPopup(null); setNearbyFacilityBbox(null); setFacilityKeys(new Set()); }}>초기화</ResetButton>
          </div>
        ) : null}

        {mapMode === 'medical' ? (
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
        ) : null}

      </section>

      <div className="fixed right-6 top-6 z-[1200] grid justify-items-end gap-1.5">
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link
            to={user ? '/mypage' : '/login'}
            className="app-floating-button h-10 min-h-10"
          >
            {user ? '마이페이지' : '로그인'}
          </Link>
        </div>
        <div className="grid translate-x-[-10px] justify-items-end gap-0.5 text-[11px] font-semibold leading-4 text-text">
          <Link className="bg-transparent p-0 hover:text-text" to="/terms">이용약관</Link>
          <Link className="bg-transparent p-0 hover:text-text" to="/privacy">개인정보처리방침</Link>
          <Link className="bg-transparent p-0 hover:text-text" to="/data-sources">데이터 출처</Link>
        </div>
      </div>

      <div className="absolute bottom-6 left-6 z-[500] flex items-center gap-2">
        <button
          type="button"
          onClick={handleDashboardOpen}
          className="app-floating-button"
        >
          대시보드 보기
        </button>
        <span className="group relative inline-flex">
        <button
          type="button"
          onClick={() => setLocateRequest((v) => v + 1)}
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
        {user ? <span className="group relative inline-flex">
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
            setHomeRequest((v) => v + 1);
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
        </span> : null}
        {user ? <span className="group relative inline-flex">
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
            setSchoolRequest((v) => v + 1);
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
        </span> : null}
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
              <path d="M5 11.25 12 5l7 6.25" />
              <path d="M7 10.5V19h10v-8.5" />
              <path d="M10.25 19v-4.25h3.5V19" />
              {!showHomeMarker ? <path d="M4.5 4.5 19.5 19.5" /> : null}
            </svg>
          </button>
          <IconTooltip>{showHomeMarker ? '집 마커 숨기기' : '집 마커 표시'}</IconTooltip>
          </span>
        ) : null}
      </div>
      {mapMode === 'heatmap' ? (
        <div className="absolute bottom-6 left-1/2 z-[440] flex -translate-x-1/2 items-center gap-3 rounded-card border border-border bg-surface/95 px-4 py-2 text-[13px] font-semibold text-text shadow-lg backdrop-blur">
          <span>낮음</span>
          <div className="flex h-3 w-[180px] overflow-hidden rounded-full border border-border/50" aria-label="히트맵 5단계 범례">
            {HEATMAP_COLORS_ORDERED.map((color, index) => (
              <span key={`${color}-${index}`} className="h-full flex-1" style={{ backgroundColor: color }} />
            ))}
          </div>
          <span>높음</span>
          <strong className="text-[var(--color-heatmap-5)]">{HEAT_LAYERS.find((l) => l.key === heatLayer)?.label}</strong>
        </div>
      ) : null}

      {mapMode !== 'heatmap' && selectedPlacePin ? (
        <div className="absolute bottom-6 left-1/2 z-[520] flex -translate-x-1/2 items-center gap-2 rounded-card border border-border bg-surface/95 p-2 shadow-lg backdrop-blur" aria-label={'\uc9c0\uc815 \ud540 \uc791\uc5c5'}>
          <button
            type="button"
            onClick={() => {
              setSelectedPlacePin(null);
              setSelectedSearchItem(null);
            }}
            className="h-9 rounded-[var(--map-control-radius)] border border-border bg-surface px-3 text-[13px] font-semibold text-text-muted shadow-sm transition hover:bg-surface-alt hover:text-text"
          >
            {'\ud540 \uc0ad\uc81c'}
          </button>
        </div>
      ) : null}

      {scoresLoading ? <StatusPill>지도 데이터를 불러오는 중입니다.</StatusPill> : null}
      {scoresError ? <StatusPill tone="danger">지도 데이터를 불러오지 못했습니다.</StatusPill> : null}
      {mapMode === 'realestate' && (matchQuery.isFetching || rentCacheQuery.isFetching) ? <StatusPill>부동산 데이터를 불러오는 중입니다.</StatusPill> : null}
      {mapMode === 'facility' && amenitiesQuery.isFetching ? <StatusPill>{nearbyFacilityBbox ? '\uc120\ud0dd \uc9c0\uc810 \uc8fc\ubcc0 \uc2dc\uc124\uc744 \ubd88\ub7ec\uc624\ub294 \uc911\uc785\ub2c8\ub2e4.' : '시설 데이터를 불러오는 중입니다.'}</StatusPill> : null}
      {mapMode === 'medical' && medicalFacilitiesFetching ? <StatusPill>의료 데이터를 불러오는 중입니다.</StatusPill> : null}
      {toast ? <StatusPill position="top-[88px]" tone="dark">{toast}</StatusPill> : null}

      <MapPopup
        popup={popup}
        onClose={() => {
          setPopup(null);
        }}
        heatLayer={heatLayer}
        ranks={ranks}
        rankTotal={scoresData.length}
      />

      {routeTransition ? (
        <div className="map-route-transition map-route-transition--out" aria-hidden="true">
          <div className="map-route-transition__frame" />
        </div>
      ) : null}
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
