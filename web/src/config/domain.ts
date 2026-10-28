// Form limits and backend vocabulary. Kept apart from app.ts because app.ts is on the
// first-load path and only pages with forms need these.
export const domainConfig = {
  /** Server-side validation ranges, mirrored so forms reject bad input before sending. */
  limits: {
    timezoneOffsetMinutes: { min: -720, max: 840 },
    autoSkipMinutes: { min: 1, max: 100 },
    cleanupHours: { min: 1, max: 720 },
    rows: { min: 1, max: 5000 },
  },
  /** Values the backend accepts (backend INTERVAL_MAP, tv_mode, radar formulas). */
  domain: {
    fetchTimeframes: ['1h', '4h', '1d', '1w'],
    radarTimeframes: ['1W', '1D', '4H', '1H'],
    tvModes: [1, 2, 3],
    defaultRows: 80,
    dataRows: 40,
    goldRows: 60,
    stockRadarFormulas: [
      'ADVANCED_VOLUME_ANALYSIS', 'IPI', 'IFI', 'UIPT', 'UIPT_HORIZON',
      'EXTENDED_SESSION_ANALYSIS', 'ROLE_CORE_RADAR',
    ],
    stockRadarModes: ['ai', 'logic'],
    /** Backend default for Stock Radar AI calls (StockRadarRequest.model). */
    stockRadarModel: 'gemini-2.5-flash',
    /** The export endpoints treat this list name as "every symbol with history". */
    allSymbolsList: 'All Symbols',
  },
} as const
