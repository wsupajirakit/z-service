// Sidebar icon per page, keyed by the same title key as the nav label.
import type { TitleKey } from '../i18n/messageKey.ts'
import {
  ActivityIcon, BriefcaseIcon, ChartIcon, CoinsIcon, DownloadIcon, HistoryIcon, HomeIcon,
  ListIcon, MailIcon, RadarIcon, ScanIcon, SettingsIcon, type IconComponent,
} from '../components/ui/icons.tsx'

export const navIcons: Record<TitleKey, IconComponent> = {
  nav_home: HomeIcon,
  nav_dashboard: ActivityIcon,
  nav_watchlist: ListIcon,
  nav_portfolio: BriefcaseIcon,
  nav_history: HistoryIcon,
  nav_export: DownloadIcon,
  nav_radar_summary: RadarIcon,
  nav_stock_radar: ScanIcon,
  nav_earning_scan: ChartIcon,
  nav_gold: CoinsIcon,
  nav_settings: SettingsIcon,
  nav_inbound_events: MailIcon,
}
