const DASHBOARD_MAX_WIDTH = 1280;
const DASHBOARD_PAGE_PADDING = 20;
const DASHBOARD_GRID_GAP = 12;
const DASHBOARD_MINI_MAP_HEIGHT = 300;

export function dashboardLayoutVars(): React.CSSProperties {
  return {
    '--dashboard-max-width': `${DASHBOARD_MAX_WIDTH}px`,
    '--dashboard-page-padding': `${DASHBOARD_PAGE_PADDING}px`,
    '--dashboard-grid-gap': `${DASHBOARD_GRID_GAP}px`,
    '--dashboard-mini-map-height': `${DASHBOARD_MINI_MAP_HEIGHT}px`,
  } as React.CSSProperties;
}

export function setDashboardMiniMapTransitionTarget() {
  const viewportWidth = window.innerWidth;
  const containerWidth = Math.min(
    DASHBOARD_MAX_WIDTH,
    Math.max(0, viewportWidth - DASHBOARD_PAGE_PADDING * 2),
  );
  const containerLeft = (viewportWidth - containerWidth) / 2;
  const columnWidth = (containerWidth - DASHBOARD_GRID_GAP) / 2;
  const targetLeft = containerLeft + columnWidth + DASHBOARD_GRID_GAP;

  document.documentElement.style.setProperty('--map-transition-left', `${targetLeft}px`);
  document.documentElement.style.setProperty('--map-transition-top', `${DASHBOARD_PAGE_PADDING}px`);
  document.documentElement.style.setProperty('--map-transition-width', `${columnWidth}px`);
  document.documentElement.style.setProperty('--map-transition-height', `${DASHBOARD_MINI_MAP_HEIGHT}px`);
}
