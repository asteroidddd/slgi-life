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
  const outerWidth = Math.min(DASHBOARD_MAX_WIDTH, viewportWidth);
  const outerLeft = (viewportWidth - outerWidth) / 2;
  const contentWidth = Math.max(0, outerWidth - DASHBOARD_PAGE_PADDING * 2);
  const cardPadding = 12;
  const headerHeight = 40;
  const headerMarginBottom = 12;
  const gridWidth = Math.max(0, contentWidth - cardPadding * 2);
  const columnWidth = Math.max(0, (gridWidth - DASHBOARD_GRID_GAP) / 2);
  const targetLeft = outerLeft + DASHBOARD_PAGE_PADDING + cardPadding + columnWidth + DASHBOARD_GRID_GAP;
  const targetTop = DASHBOARD_PAGE_PADDING + cardPadding + headerHeight + headerMarginBottom;

  document.documentElement.style.setProperty('--map-transition-left', `${targetLeft}px`);
  document.documentElement.style.setProperty('--map-transition-top', `${targetTop}px`);
  document.documentElement.style.setProperty('--map-transition-width', `${columnWidth}px`);
  document.documentElement.style.setProperty('--map-transition-height', `${DASHBOARD_MINI_MAP_HEIGHT}px`);
}
