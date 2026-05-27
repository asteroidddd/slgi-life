// Temporary geometry helpers for the main map.
//
// The backend currently has only 5 dummy adongs and no MultiPolygon GeoJSON.
// Until step 10 (data-pipeline loads the real 426-adong GeoJSON), we render
// each adong as a small square around its centroid so the heatmap is visible.
//
// REMOVE this helper once `/public/seoul_dongs.geojson` is available and the
// HeatMap component switches to a real GeoJSON layer.
import type { LatLngBoundsLiteral } from 'leaflet';

/** Returns a closed rectangular ring around (lat, lng) of radius `halfDeg`
 *  in degrees. About 0.005° ≈ 555m at Seoul's latitude — large enough to
 *  see, small enough not to overlap five dummies that are kilometers apart.
 */
export function boundingPolygon(
  lat: number,
  lng: number,
  halfDeg = 0.005
): [number, number][] {
  return [
    [lat - halfDeg, lng - halfDeg],
    [lat - halfDeg, lng + halfDeg],
    [lat + halfDeg, lng + halfDeg],
    [lat + halfDeg, lng - halfDeg],
    [lat - halfDeg, lng - halfDeg],
  ];
}

/** Seoul-wide bounds, used for initial map view fallback. */
export const SEOUL_BOUNDS: LatLngBoundsLiteral = [
  [37.413, 126.734], // SW
  [37.715, 127.269], // NE
];
