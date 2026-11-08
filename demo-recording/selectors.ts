/** Stable UI selectors for PHAROS Dashboard verification during pitch recording */
export const SELECTORS = {
  // Main root and layout
  appRoot: "#root",
  directorOverlay: "#pitch-director-root",

  // Map & Chart canvas
  mapContainer: ".chart",
  mapCanvas: ".chart canvas",
  mapLibreGl: ".maplibregl-canvas",

  // Fleet panel
  fleetList: "[aria-label='Fleet']",
  usvCard: (id: number) => `[data-boat-id='${id}']`,
  usv01: "[data-boat-id='1']",
  usv02: "[data-boat-id='2']",
  usv03: "[data-boat-id='3']",
  usv04: "[data-boat-id='4']",
  usv05: "[data-boat-id='5']",

  // Controls & Actions
  runSimulationButton: "button:has-text('Run simulation'), button:has-text('Run')",
  pauseButton: "button:has-text('Pause')",
  resetButton: "button:has-text('Reset')",

  // Status & Decision items
  coverageHeadline: ".coverage-line, [data-testid='coverage-line']",
  decisionsPanel: "[aria-label='Decisions'], [aria-label='Attention']",
  alertsPanel: "[aria-label='Alerts']",
};
