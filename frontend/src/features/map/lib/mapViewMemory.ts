export type SavedMapMode = 'plain' | 'heatmap' | 'realestate' | 'facility' | 'medical';

export interface SavedMapView {
  center: [number, number];
  zoom: number;
  mode: SavedMapMode;
}

let savedMapView: SavedMapView | null = null;

export function saveMapView(view: SavedMapView) {
  savedMapView = view;
}

export function getSavedMapView() {
  return savedMapView;
}
