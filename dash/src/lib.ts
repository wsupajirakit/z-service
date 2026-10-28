import { SYMBOLS } from './symbols';
export { SYMBOLS };
export { API_BASE, SERVER_SYMBOLS, allSymbols, loadServerSymbols } from './core';


// Display timezone options. Stored server-side as a fixed UTC offset (minutes),
// so both the web table and the Telegram notifications render the same time.
export const TIMEZONE_OPTIONS: { label: string; offset: number }[] = [
  { label: 'UTC-08:00 (Los Angeles)', offset: -480 },
  { label: 'UTC-05:00 (New York)', offset: -300 },
  { label: 'UTC+00:00 (UTC / London)', offset: 0 },
  { label: 'UTC+01:00 (Berlin / Paris)', offset: 60 },
  { label: 'UTC+03:00 (Moscow)', offset: 180 },
  { label: 'UTC+04:00 (Dubai)', offset: 240 },
  { label: 'UTC+05:30 (India)', offset: 330 },
  { label: 'Asia/Bangkok (UTC+7)', offset: 420 },
  { label: 'UTC+08:00 (Singapore / Hong Kong)', offset: 480 },
  { label: 'UTC+09:00 (Tokyo)', offset: 540 },
];

// Format an ISO timestamp at a fixed UTC offset (minutes), giving a
// viewer-independent "YYYY-MM-DD HH:MM:SS" that matches Telegram's format.
export const formatTs = (iso: string, offsetMinutes: number): string => {
  if (!iso) return '';
  // Old rows were stored as naive UTC (no offset) — treat those as UTC so they
  // don't get re-interpreted as the viewer's local time.
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso);
  const d = new Date(hasTz ? iso : iso + 'Z');
  if (isNaN(d.getTime())) return iso;
  const shifted = new Date(d.getTime() + offsetMinutes * 60000);
  return shifted.toISOString().slice(0, 19).replace('T', ' ');
};


export const EXCHANGES = [
  'NASDAQ', 'NYSE', 'AMEX', 'CBOE', 'BINANCE', 'TVC', 'BLACKBULL', 'OANDA', 'USI', 'FX_IDC'
];

// Earning Scan only covers US-listed equities (earnings providers key off plain
// US tickers, no exchange prefix) — filter out FX/crypto/index/ETF-on-other-exchanges.
export const US_STOCK_SYMBOLS = SYMBOLS.filter(s => s.exchange === 'NASDAQ' || s.exchange === 'NYSE');

export interface TradeData {
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  EMA_20: number | null;
  EMA_50: number | null;
  EMA_100: number | null;
  EMA_200: number | null;
  RSI: number | null;
  OBV: number | null;
  CMF: number | null;
  VWAP: number | null;
  FVG: number | null;
  RVOL: number | null;
  RVOL_Deviation: number | null;
  IPI: number | null;
  IPI_Status: string | null;
}

export interface HistorySummary {
  id: number;
  timestamp: string;
  symbol: string;
  exchange: string;
  interval: string;
  extended_session: boolean;
}

// Unified server-side job status (GET /api/automate/status) — covers both the
// one-shot custom export job and the continuous auto loop.
export interface AutomateJob {
  mode: 'idle' | 'custom' | 'auto';
  status: 'idle' | 'running' | 'done' | 'error' | 'stopped';
  round: number;
  timeframes: string[];
  current_tf: string | null;
  current_symbol: string | null;
  current: number;
  total: number;
  step_index: number;
  step_total: number;
  phase: 'idle' | 'fetching' | 'cooldown';
  cooldown_until: string | null;
  failed: string[];
  started_at: string | null;
  finished_at: string | null;
  last_round_finished_at: string | null;
  message: string;
  logs: string[];
}

// TradingView connection test (POST /api/tv/test) — the "Test connection" button
// shows these log lines as a summary in a modal.
export interface ConnTestLog {
  time: string;
  level: 'info' | 'ok' | 'warn' | 'error';
  message: string;
}
export interface ConnTestResult {
  ok: boolean;
  verdict: string;
  verdict_level: string;
  passed: number;
  total: number;
  duration: number;
  logs: ConnTestLog[];
}

// Theme-safe tints for a connection-test verdict / log line (light and dark).
export const connLevelClasses: Record<string, string> = {
  ok: 'bg-success-soft text-success-soft-foreground border border-success/20',
  warn: 'bg-warning-soft text-warning-soft-foreground border border-warning/20',
  error: 'bg-danger-soft text-danger-soft-foreground border border-danger/20',
  info: 'bg-surface-secondary text-muted border border-separator',
};

// Shared widgets live in components/*.tsx (fast refresh needs component-only files);
// they are re-exported here so pages keep importing them from lib.
export { Autocomplete, type AutocompleteOption, type AutocompleteProps } from './components/Autocomplete';
export { ConfirmationModal, type ConfirmationModalProps } from './components/ConfirmationModal';
export { Countdown } from './components/Countdown';
export { ResultTable } from './components/ResultTable';
export { SymbolHistoryChart, type SymbolHistoryChartProps } from './components/SymbolHistoryChart';

// ---------------------------------------------------------------------------
// Gold trading page — pick a market source + Gemini model, then get a
// short-term (day/swing) Long/Short entry plan analysed from multi-TF data + news.
// ---------------------------------------------------------------------------
export interface GoldSource { label: string; exchange: string; }
export interface GoldModel { name: string; displayName: string; }
export interface GoldAnalysis {
  source_label: string;
  model: string;
  latest_price: number | null;
  timeframes: string[];
  news_count: number;
  analysis: string;
  generated_at: string;
}

// Minimal Markdown → HTML for the analysis text (headings, bold, list items).
export function renderMarkdown(md: string): string {
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return esc(md)
    .replace(/^### (.*)$/gm, '<h4 class="font-bold text-foreground mt-4 mb-1">$1</h4>')
    .replace(/^## (.*)$/gm, '<h3 class="text-lg font-bold text-amber-700 dark:text-amber-400 mt-5 mb-2">$1</h3>')
    .replace(/^# (.*)$/gm, '<h2 class="text-xl font-bold text-foreground mt-5 mb-2">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-foreground">$1</strong>')
    .replace(/^\s*[-*] (.*)$/gm, '<li class="ml-5 list-disc">$1</li>')
    .replace(/\n{2,}/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

export const EARNING_SCAN_PROVIDER_LABELS: Record<string, string> = {
  finnhub: 'Finnhub',
  fmp: 'Financial Modeling Prep',
  alpha_vantage: 'Alpha Vantage',
};
