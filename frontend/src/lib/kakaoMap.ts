// Kakao Maps SDK loader + GeoJSON path conversion utilities.
//
// 카카오맵 JS 키는 frontend/.env의 VITE_KAKAO_JS_KEY. 미설정 시 useKakaoLoader가
// 에러를 반환하므로 호출부는 isError 분기로 안내 메시지를 띄운다.

import { useKakaoLoader } from 'react-kakao-maps-sdk';

const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_JS_KEY as string | undefined;

/**
 * 모든 카카오맵 컴포넌트의 진입점에서 호출. SDK 로드 상태를 반환한다.
 * services 라이브러리는 서비스 검색/지오코딩에 필요 (현재 미사용이지만 미리 옵션).
 */
export function useKakao(): { loading: boolean; error: unknown } {
  const [loading, error] = useKakaoLoader({
    appkey: KAKAO_JS_KEY ?? '',
    libraries: ['services'],
  });
  return { loading, error: KAKAO_JS_KEY ? error : new Error('VITE_KAKAO_JS_KEY 미설정') };
}

type LatLng = { lat: number; lng: number };

/**
 * GeoJSON Polygon/MultiPolygon → 카카오맵 Polygon path 배열들.
 *
 * 반환 타입은 sub-polygon 단위 분리:
 *   [
 *     [outer_ring, hole1, hole2, ...],   // sub-polygon 1
 *     [outer_ring, hole1, ...],          // sub-polygon 2
 *     ...
 *   ]
 *
 * 호출부는 sub-polygon 개수만큼 `<Polygon>`을 그려야 한다.
 * (단일 `<Polygon>`에 모든 sub-polygon ring을 평탄화해 넣으면 카카오 SDK가
 *  outer + hole 의미로 잘못 해석한다.)
 *
 * 좌표 변환: GeoJSON [lng, lat] → 카카오 {lat, lng}.
 */
export function geoJsonToKakaoPolygons(
  coordinates: number[][][] | number[][][][],
  geomType: 'Polygon' | 'MultiPolygon',
): LatLng[][][] {
  const toLatLng = ([lng, lat]: number[]): LatLng => ({ lat, lng });

  if (geomType === 'Polygon') {
    // Polygon: [outer_ring, hole1, ...] — 단일 sub-polygon
    const rings = coordinates as number[][][];
    return [rings.map((ring) => ring.map(toLatLng))];
  }

  // MultiPolygon: [[outer, hole1, ...], [outer, ...], ...]
  const polys = coordinates as number[][][][];
  return polys.map((poly) => poly.map((ring) => ring.map(toLatLng)));
}
