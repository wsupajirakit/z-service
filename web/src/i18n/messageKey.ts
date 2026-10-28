// Nav titles are looked up by key from route staticData. Indexing the whole `m` namespace with a
// runtime key defeats tree-shaking and put every message (all 3 locales) in the entry chunk, so
// the lookup goes through this explicit map instead. A new tab adds its nav_* message here.
import {
  nav_dashboard, nav_earning_scan, nav_export, nav_gold, nav_history, nav_home, nav_inbound_events,
  nav_portfolio, nav_radar_summary, nav_settings, nav_stock_radar, nav_watchlist,
} from '../paraglide/messages.js'

const titles = {
  nav_dashboard, nav_earning_scan, nav_export, nav_gold, nav_history, nav_home, nav_inbound_events,
  nav_portfolio, nav_radar_summary, nav_settings, nav_stock_radar, nav_watchlist,
} satisfies Record<string, () => string>

export type TitleKey = keyof typeof titles

export function translateTitle(key: TitleKey): string {
  return titles[key]()
}
