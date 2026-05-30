import { useEffect, useMemo } from 'react';
import L from 'leaflet';
import { Marker, useMap, useMapEvents } from 'react-leaflet';

import type { MapSearchItem } from '@/types/api';
import type { MapState } from '@/components/Map/TransactionPinLayer';

interface AiMapTarget {
  label: string;
  lat: number;
  lng: number;
}

export type SelectedPlacePinSource = 'map-click' | 'search' | 'current-location' | 'home';

export interface SelectedPlacePin {
  lat: number;
  lng: number;
  label: string;
  source: SelectedPlacePinSource;
}

export function HomeMarker({ lat, lng, onClick }: { lat?: number | null; lng?: number | null; onClick: () => void }) {
  const map = useMap();
  const icon = useMemo(() => L.divIcon({
    className: 'home-marker-icon',
    html: `<img class="home-logo-marker" src="/home-marker.png" alt="" />`,
    iconSize: [38, 50],
    iconAnchor: [19, 50],
  }), []);

  if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  return (
    <Marker
      position={[lat, lng]}
      icon={icon}
      interactive
      zIndexOffset={1100}
      eventHandlers={{
        click: (event) => {
          event.originalEvent.stopPropagation();
          map.flyTo([lat, lng], Math.max(map.getZoom(), 15), { duration: 0.35 });
          onClick();
        },
      }}
    />
  );
}

export function AiMapTargetLayer({ target }: { target: AiMapTarget | null }) {
  const map = useMap();
  const icon = useMemo(() => L.divIcon({
    className: 'ai-map-marker-icon',
    html: '<div class="ai-map-pin"></div>',
    iconSize: [30, 42],
    iconAnchor: [15, 42],
  }), []);

  useEffect(() => {
    if (!target) return;
    map.flyTo([target.lat, target.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
  }, [map, target]);

  if (!target) return null;

  return (
    <Marker
      position={[target.lat, target.lng]}
      icon={icon}
      interactive
      zIndexOffset={950}
      eventHandlers={{
        click: (event) => {
          event.originalEvent.stopPropagation();
          map.flyTo([target.lat, target.lng], Math.max(map.getZoom(), 15), { duration: 0.35 });
        },
      }}
    />
  );
}



export function hasValidCoordinate(item: MapSearchItem | null): item is MapSearchItem {
  return !!item && Number.isFinite(item.lat) && Number.isFinite(item.lng);
}

export function SearchFlyTo({ item }: { item: MapSearchItem | null }) {
  const map = useMap();
  useEffect(() => {
    if (!hasValidCoordinate(item)) return;
    map.flyTo([item.lat, item.lng], Math.max(map.getZoom(), 17), { duration: 0.6 });
  }, [item, map]);
  return null;
}

export function SearchMarkerLayer({ item }: { item: MapSearchItem | null }) {
  if (!hasValidCoordinate(item)) return null;
  return <SelectedPlacePinLayer pin={{ lat: item.lat, lng: item.lng, label: item.name, source: 'search' }} />;
}

export function MapClickSelectLayer({
  enabled,
  onSelect,
}: {
  enabled: boolean;
  onSelect: (pin: SelectedPlacePin) => void;
}) {
  useMapEvents({
    click: (event) => {
      if (!enabled) return;
      const target = event.originalEvent.target as HTMLElement | null;
      if (target?.closest('.leaflet-marker-icon, .leaflet-popup, .leaflet-control, button, a, input, textarea, select')) {
        return;
      }
      onSelect({
        lat: event.latlng.lat,
        lng: event.latlng.lng,
        label: '\uc9c0\uc815\ud55c \uc704\uce58',
        source: 'map-click',
      });
    },
  });
  return null;
}

export function SelectedPlacePinLayer({ pin }: { pin: SelectedPlacePin | null }) {
  const map = useMap();
  const icon = useMemo(() => L.divIcon({
    className: 'selected-place-marker-icon',
    html: '<span class="selected-place-marker" aria-hidden="true"><span class="selected-place-marker__head"><span class="selected-place-marker__dot"></span></span><span class="selected-place-marker__tail"></span><span class="selected-place-marker__ring"></span></span>',
    iconSize: [34, 46],
    iconAnchor: [17, 42],
  }), []);

  if (!pin) return null;

  return (
    <Marker
      position={[pin.lat, pin.lng]}
      icon={icon}
      interactive
      zIndexOffset={850}
      eventHandlers={{
        click: (event) => {
          event.originalEvent.stopPropagation();
          map.flyTo([pin.lat, pin.lng], Math.max(map.getZoom(), 17), { duration: 0.35 });
        },
      }}
    />
  );
}

export function CurrentLocationLayer({
  requestId,
  onError,
  onLocated,
}: {
  requestId: number;
  onError: (message: string) => void;
  onLocated?: (lat: number, lng: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (requestId === 0) return;
    if (!navigator.geolocation) {
      onError('현재 위치를 지원하지 않는 브라우저입니다.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        map.flyTo(
          [lat, lng],
          Math.max(map.getZoom(), 15),
          { duration: 0.6 },
        );
        onLocated?.(lat, lng);
      },
      () => onError('현재 위치 권한을 확인해주세요.'),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 },
    );
  // Intentionally depend only on requestId: parent passes an inline onError callback.
  // Including it here retriggers flyTo on unrelated renders, making the map feel locked.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, requestId]);

  return null;
}

export function HomeLocationLayer({
  requestId,
  lat,
  lng,
  onError,
  onLocated,
}: {
  requestId: number;
  lat?: number | null;
  lng?: number | null;
  onError: (message: string) => void;
  onLocated?: (lat: number, lng: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (requestId === 0) return;
    if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      onError('집 주소 좌표가 없습니다. 마이페이지에서 주소를 확인해주세요.');
      return;
    }
    map.flyTo([lat, lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
    onLocated?.(lat, lng);
  // Intentionally depend only on requestId: parent passes an inline onError callback.
  // Including it here retriggers flyTo on unrelated renders, making the map feel locked.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, requestId]);

  return null;
}

export function MapStateProbe({ onMapStateChange }: { onMapStateChange: (state: MapState) => void }) {
  const map = useMap();
  useEffect(() => {
    const b = map.getBounds();
    onMapStateChange({
      bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() },
      zoom: map.getZoom(),
    });
  }, [map, onMapStateChange]);
  useMapEvents({
    moveend: () => {
      const b = map.getBounds();
      onMapStateChange({ bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() }, zoom: map.getZoom() });
    },
    zoomend: () => {
      const b = map.getBounds();
      onMapStateChange({ bbox: { lng1: b.getWest(), lat1: b.getSouth(), lng2: b.getEast(), lat2: b.getNorth() }, zoom: map.getZoom() });
    },
  });
  return null;
}
