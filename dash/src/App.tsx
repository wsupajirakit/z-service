import { Button, Chip, Modal, Spinner, TextArea, Toast, Tooltip } from '@heroui/react';
import axios from 'axios';
import {
  Activity, CalendarClock, Coins, Download, Eraser, History, KeyRound, LayoutDashboard,
  PanelLeftClose, PanelLeftOpen, Radar, Sparkles, Star, Wallet, type LucideIcon,
} from 'lucide-react';
import { lazy, Suspense, useEffect, useState } from 'react';
import { I18nProvider } from 'react-aria-components';
import { AccountMenu } from './components/AccountMenu';
import { ConfirmProvider } from './components/confirm';
import { useConfirm } from './components/confirmContext';
import { LanguageSwitch, ThemeSwitch } from './components/Preferences';
import { errorDetail, notify } from './components/notify';
import { useLang, useT, type Lang, type MessageKey } from './i18n';
import { common } from './i18n/messages/common';
import { shell } from './i18n/messages/shell';
import { API_BASE, loadServerSymbols } from './core';
import { SYMBOLS } from './symbols';

type ShellKey = MessageKey<typeof shell>;

type VersionInfo = {
  version?: string; commit?: string; build_time?: string; symbols_count?: number;
  job_phase?: string; job_round?: number; job_total?: number;
};

function VersionBadge({ apiBase }: { apiBase: string }) {
  const t = useT(shell);
  const [v, setV] = useState<VersionInfo | null>(null);
  const [clientCount, setClientCount] = useState(SYMBOLS.length);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await axios.get<VersionInfo>(`${apiBase}/api/version`);
        if (alive) setV(r.data);
      } catch { /* the badge keeps the last answer */ }
      const n = await loadServerSymbols(apiBase);
      if (alive) setClientCount(n);
    };
    void load();
    const timer = setInterval(load, 60000);
    return () => { alive = false; clearInterval(timer); };
  }, [apiBase]);
  const stale = Boolean(v?.version && v.version !== __APP_VERSION__);
  const phase = v?.job_phase || 'idle';
  const dot = phase === 'fetching' ? 'bg-success animate-pulse' : phase === 'cooldown' ? 'bg-warning' : 'bg-muted';
  const commit = v?.commit && v.commit !== 'unknown' ? v.commit.slice(0, 7) : '';
  const title = t('versionTitle', {
    client: __APP_VERSION__, built: __BUILD_TIME__, server: v?.version ?? '?', commit,
    serverBuilt: v?.build_time ?? '?', phase, round: v?.job_round ?? 0, total: v?.job_total ?? 0,
  });
  return (
    <Tooltip delay={200}>
      <Tooltip.Trigger>
        <Chip color={stale ? 'warning' : 'default'} variant="soft" className="hidden shrink-0 gap-1.5 font-mono xl:inline-flex">
          <span className={`size-2 rounded-full ${dot}`} />
          <Chip.Label>
            v{v?.version ?? __APP_VERSION__} · {v?.symbols_count ?? clientCount}{stale ? ' · ↻' : ''}
          </Chip.Label>
        </Chip>
      </Tooltip.Trigger>
      <Tooltip.Content className="max-w-sm text-xs">
        {t('symbols', { n: v?.symbols_count ?? clientCount })}{commit ? ` · ${commit}` : ''}{stale ? ` · ${t('staleClient')}` : ''}
        <br />{title}
      </Tooltip.Content>
    </Tooltip>
  );
}

function TvTokenButton({ apiBase }: { apiBase: string }) {
  const t = useT(shell);
  const tc = useT(common);
  const [open, setOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [status, setStatus] = useState<'active' | 'expired' | 'none' | null>(null);
  const [expiresIn, setExpiresIn] = useState(0);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${apiBase}/api/settings/tv_token`);
        setStatus(res.data.status);
        if (res.data.expires_in_minutes) setExpiresIn(res.data.expires_in_minutes);
      } catch { /* the button shows "not set" until the next poll */ }
    };
    void load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [apiBase]);

  const save = async () => {
    if (!tokenInput.trim()) { notify.warning(t('tokenEmpty')); return; }
    setSaving(true);
    try {
      const res = await axios.post(`${apiBase}/api/settings/tv_token`, { token: tokenInput.trim() });
      setStatus(res.data.status);
      setExpiresIn(res.data.expires_in_minutes);
      setTokenInput('');
      setOpen(false);
      notify.success(t('tokenSaved'));
    } catch (err) {
      notify.error(t('tokenFailed', { detail: errorDetail(err) }));
    } finally {
      setSaving(false);
    }
  };

  const active = status === 'active';
  const label = active ? t('tokenActive', { minutes: expiresIn }) : status === 'expired' ? t('tokenExpired') : t('tokenNone');
  return (
    <>
      <Tooltip delay={200}>
        <Button size="sm" variant={active ? 'secondary' : 'danger-soft'} onPress={() => setOpen(true)}>
          <KeyRound className="size-4" />
          <span className="hidden xl:inline">{t('token')}</span>
        </Button>
        <Tooltip.Content>{t('tokenTitle')}: {label}</Tooltip.Content>
      </Tooltip>
      <Modal.Backdrop isOpen={open} onOpenChange={setOpen}>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[460px]">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon className="bg-accent-soft text-accent-soft-foreground"><KeyRound className="size-5" /></Modal.Icon>
              <Modal.Heading>{t('tokenTitle')}</Modal.Heading>
            </Modal.Header>
            <Modal.Body className="space-y-4">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted">{t('tokenStatus')}</span>
                <Chip size="sm" variant="soft" color={active ? 'success' : status === 'expired' ? 'danger' : 'default'}>{label}</Chip>
              </div>
              <TextArea aria-label={t('tokenPaste')} placeholder="eyJhbGc…" value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)} rows={5} className="w-full font-mono text-sm" />
              <p className="text-xs text-muted">{t('tokenHint')}</p>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="tertiary" slot="close">{tc('cancel')}</Button>
              <Button onPress={save} isPending={saving}>{saving ? tc('saving') : tc('save')}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </>
  );
}

function CleanupButton({ apiBase }: { apiBase: string }) {
  const t = useT(shell);
  const confirm = useConfirm();
  const [busy, setBusy] = useState(false);
  const run = async () => {
    if (!(await confirm({ title: t('cleanupTitle'), body: t('cleanupBody'), confirmLabel: t('cleanup') }))) return;
    setBusy(true);
    try {
      const res = await axios.post(`${apiBase}/api/history/cleanup?hours=2`);
      notify.success(t('cleanupDone', { message: res.data.message, rows: res.data.rows_after }));
    } catch (err) {
      notify.error(t('cleanupFailed', { detail: errorDetail(err) }));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Tooltip delay={200}>
      <Button size="sm" variant="tertiary" onPress={run} isPending={busy}>
        <Eraser className="size-4" />
        <span className="hidden xl:inline">{busy ? t('cleaning') : t('cleanup')}</span>
      </Button>
      <Tooltip.Content>{t('cleanupTitle')}</Tooltip.Content>
    </Tooltip>
  );
}

type TabId = 'dashboard' | 'gold' | 'radar' | 'radar_summary' | 'earning_scan' | 'watchlist' | 'portfolio' | 'history' | 'export';

// Each page: its hash, label, icon and the tint of its icon tile.
const PAGES: { id: TabId, label: ShellKey, icon: LucideIcon, tint: string }[] = [
  { id: 'dashboard', label: 'navDashboard', icon: LayoutDashboard, tint: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  { id: 'gold', label: 'navGold', icon: Coins, tint: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' },
  { id: 'radar', label: 'navRadar', icon: Sparkles, tint: 'bg-violet-500/15 text-violet-600 dark:text-violet-400' },
  { id: 'radar_summary', label: 'navRadarSummary', icon: Radar, tint: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400' },
  { id: 'earning_scan', label: 'navEarningScan', icon: CalendarClock, tint: 'bg-teal-500/15 text-teal-600 dark:text-teal-400' },
  { id: 'watchlist', label: 'navWatchlist', icon: Star, tint: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400' },
  { id: 'portfolio', label: 'navPortfolio', icon: Wallet, tint: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' },
  { id: 'history', label: 'navHistory', icon: History, tint: 'bg-slate-500/15 text-slate-600 dark:text-slate-300' },
  { id: 'export', label: 'navExport', icon: Download, tint: 'bg-rose-500/15 text-rose-600 dark:text-rose-400' },
];
// Pages that use the whole screen below the header (their own panes and scrolling).
const FULL_BLEED = new Set<TabId>(['watchlist']);

const tabFromHash = (): TabId => {
  const h = window.location.hash.replace(/^#/, '');
  return PAGES.find((p) => p.id === h)?.id ?? 'dashboard';
};

// Each page is its own chunk, fetched the first time it is opened.
const DashboardView = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardView })));
const GoldView = lazy(() => import('./pages/GoldPage').then((m) => ({ default: m.GoldView })));
const StockRadarView = lazy(() => import('./pages/StockRadarPage').then((m) => ({ default: m.StockRadarView })));
const RadarView = lazy(() => import('./RadarView'));
const EarningScanView = lazy(() => import('./pages/EarningScanPage').then((m) => ({ default: m.EarningScanView })));
const WatchlistView = lazy(() => import('./pages/WatchlistPage').then((m) => ({ default: m.WatchlistView })));
const PortfolioView = lazy(() => import('./pages/PortfolioPage').then((m) => ({ default: m.PortfolioView })));
const HistoryView = lazy(() => import('./pages/HistoryPage').then((m) => ({ default: m.HistoryView })));
const ExportView = lazy(() => import('./pages/ExportPage').then((m) => ({ default: m.ExportView })));

function PageLoading() {
  const t = useT(common);
  return (
    <div role="status" className="grid min-h-[40vh] place-items-center text-muted">
      <span className="flex items-center gap-2 text-sm"><Spinner size="sm" />{t('loading')}</span>
    </div>
  );
}

function PageView({ tab }: { tab: TabId }) {
  switch (tab) {
    case 'gold': return <GoldView />;
    case 'radar': return <StockRadarView />;
    case 'radar_summary': return <RadarView />;
    case 'earning_scan': return <EarningScanView />;
    case 'watchlist': return <WatchlistView />;
    case 'portfolio': return <PortfolioView />;
    case 'history': return <HistoryView />;
    case 'export': return <ExportView />;
    default: return <DashboardView />;
  }
}

const isNarrow = () => window.innerWidth < 1024;

function Shell() {
  const t = useT(shell);
  const [activeTab, setActiveTab] = useState<TabId>(tabFromHash);
  // Wide screens: the menu is either full or icons only. Narrow screens: a drawer.
  const [expanded, setExpanded] = useState(!isNarrow());

  // Menu items are real <a href="#tab"> links, so they open in a new tab with a modifier
  // or middle click; this listener follows the hash (also back/forward and deep links).
  useEffect(() => {
    const onHash = () => setActiveTab(tabFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const current = PAGES.find((p) => p.id === activeTab) ?? PAGES[0];
  const CurrentIcon = current.icon;
  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-separator bg-surface transition-[width,transform] duration-300 lg:sticky lg:top-0 lg:h-screen ${
        expanded ? 'w-64 translate-x-0' : 'w-64 -translate-x-full lg:w-[72px] lg:translate-x-0'}`}>
        <div className="flex h-16 items-center gap-3 px-4 border-b border-separator">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground shadow-sm">
            <Activity className="size-5" />
          </span>
          <div className={`min-w-0 ${expanded ? '' : 'lg:hidden'}`}>
            <div className="truncate font-semibold leading-tight">Z-Service</div>
            <div className="truncate text-xs text-muted">{t('brandTagline')}</div>
          </div>
        </div>
        <nav aria-label={t('menu')} className="flex-1 space-y-1 overflow-y-auto p-3">
          {PAGES.map((item) => {
            const active = item.id === activeTab;
            const link = (
              <a key={item.id} href={`#${item.id}`} aria-current={active ? 'page' : undefined}
                onClick={() => { setActiveTab(item.id); if (isNarrow()) setExpanded(false); }}
                className={`group flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm font-medium no-underline outline-none transition-colors focus-visible:ring-2 focus-visible:ring-focus ${
                  active ? 'bg-accent-soft text-accent-soft-foreground' : 'text-muted hover:bg-surface-secondary hover:text-foreground'}`}>
                <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${item.tint} ${active ? 'ring-1 ring-current/30' : ''}`}>
                  <item.icon className="size-4" />
                </span>
                <span className={`truncate ${expanded ? '' : 'lg:hidden'}`}>{t(item.label)}</span>
              </a>
            );
            return expanded ? link : (
              <Tooltip key={item.id} delay={150}>
                {link}
                <Tooltip.Content placement="right">{t(item.label)}</Tooltip.Content>
              </Tooltip>
            );
          })}
        </nav>
      </aside>

      {expanded ? (
        <button type="button" aria-label={t('collapse')} onClick={() => setExpanded(false)}
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden" />
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-separator bg-background/80 px-4 backdrop-blur-md">
          <Tooltip delay={200}>
            <Button isIconOnly size="sm" variant="ghost" aria-label={expanded ? t('collapse') : t('expand')}
              onPress={() => setExpanded(!expanded)}>
              {expanded ? <PanelLeftClose className="size-5" /> : <PanelLeftOpen className="size-5" />}
            </Button>
            <Tooltip.Content>{expanded ? t('collapse') : t('expand')}</Tooltip.Content>
          </Tooltip>
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${current.tint}`}>
              <CurrentIcon className="size-4" />
            </span>
            <h1 className="truncate text-base font-semibold">{t(current.label)}</h1>
          </div>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <VersionBadge apiBase={API_BASE} />
            <CleanupButton apiBase={API_BASE} />
            <TvTokenButton apiBase={API_BASE} />
            <div className="hidden items-center gap-2 lg:flex">
              <LanguageSwitch />
              <ThemeSwitch />
            </div>
            <AccountMenu />
          </div>
        </header>

        <main className={FULL_BLEED.has(activeTab) ? 'h-[calc(100dvh-4rem)] min-h-0' : 'flex-1 p-4 md:p-8'}>
          <div className={FULL_BLEED.has(activeTab) ? 'h-full' : 'mx-auto max-w-6xl space-y-6'}>
            <Suspense fallback={<PageLoading />}>
              <PageView tab={activeTab} />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}

// Dates, numbers and HeroUI's own labels follow the chosen language too.
const LOCALES: Record<Lang, string> = { en: 'en-US', th: 'th-TH' };

function App() {
  const lang = useLang();
  return (
    <I18nProvider locale={LOCALES[lang]}>
      <ConfirmProvider>
        <Shell />
        <Toast.Provider placement="top end" />
      </ConfirmProvider>
    </I18nProvider>
  );
}

export default App;
