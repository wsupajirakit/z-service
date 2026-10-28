// What the shell needs at start-up, kept apart from lib.ts so the first page load does not
// pull in the chart library and the shared widgets.
import axios from 'axios';
import { SYMBOLS } from './symbols';

// Empty (relative, same-origin) in production — the FastAPI container serves this build.
// In dev, .env.development sets VITE_API_BASE to the local backend (http://localhost:9999).
export const API_BASE = import.meta.env.VITE_API_BASE ?? '';

// Server-side symbol list (/api/symbols = build symbols ∪ DB watchlist symbols with exchange).
// Filled once at app load; Auto All / Automate All use the union so a symbol added via the API
// is fetched without waiting for a frontend rebuild.
export let SERVER_SYMBOLS: { symbol: string; name: string; exchange: string }[] = [];
export function allSymbols() {
  const seen = new Set(SYMBOLS.map((s) => s.symbol));
  return [...SYMBOLS, ...SERVER_SYMBOLS.filter((s) => !seen.has(s.symbol))];
}

export async function loadServerSymbols(apiBase: string) {
  try {
    const r = await axios.get<{ count: number; symbols: { symbol: string; name: string; exchange: string }[] }>(`${apiBase}/api/symbols`);
    if (Array.isArray(r.data?.symbols)) SERVER_SYMBOLS = r.data.symbols;
  } catch { /* server list unavailable -> fall back to the baked SYMBOLS */ }
  return allSymbols().length;
}
