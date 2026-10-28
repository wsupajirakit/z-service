import {
  Alert, Button, Card, Checkbox, Chip, Description, Input, Label, ListBox, Modal, ProgressBar, Select, Spinner,
  TextField, Tooltip, type Key,
} from '@heroui/react';
import axios from 'axios';
import {
  Activity, CheckCircle2, CloudDownload, Database, Inbox, Info, Layers, Repeat, RefreshCw, SlidersHorizontal, Square, Timer,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { notify } from '../components/notify';
import { SectionHeader } from '../components/SectionHeader';
import { useT, type MessageKey } from '../i18n';
import { common } from '../i18n/messages/common';
import { dashboard } from '../i18n/messages/dashboard';
import {
  API_BASE, Autocomplete, ConfirmationModal, Countdown, EXCHANGES, ResultTable, SYMBOLS, allSymbols, connLevelClasses,
  type AutomateJob, type ConnTestResult, type TradeData,
} from '../lib';
import { useStickToBottom } from '../useStickToBottom';

type DashKey = MessageKey<typeof dashboard>;
type WatchItem = { symbol: string; exchange?: string; name?: string };
type Target = { symbol: string; exchange: string };
type ConfirmKind = 'startAuto' | 'stopAuto' | 'stopCustom';
type FetchError = { detail?: string; key?: 'fetchFailed' | 'noServer' };

const ALL = 'All Symbols';
const INTERVALS = ['15m', '30m', '1h', '4h', '1d', '1w'];
const CUSTOM_TFS = ['1h', '4h', '1d', '1w'];
const TV_MODES: { id: string; label: DashKey }[] = [
  { id: '1', label: 'tvMode1' }, { id: '2', label: 'tvMode2' }, { id: '3', label: 'tvMode3' },
];
const AUTO_STEPS: { interval: string; extendedSession: boolean; label: DashKey }[] = [
  { interval: '1h', extendedSession: true, label: 'step1h' },
  { interval: '4h', extendedSession: true, label: 'step4h' },
  { interval: '1d', extendedSession: false, label: 'step1d' },
  { interval: '1w', extendedSession: false, label: 'step1w' },
];
const TF_LABEL: Record<string, DashKey> = {
  '15m': 'tf15m', '30m': 'tf30m', '1h': 'tf1h', '4h': 'tf4h', '1d': 'tf1d', '1w': 'tf1w',
};
const EMPTY_PROGRESS = { current: 0, total: 0, currentSymbol: '', logs: [] as string[] };

const stripTf = (s: string) => (s.includes(':') ? s.slice(s.indexOf(':') + 1) : s);
const pct = (n: number, total: number) => (total > 0 ? Math.round((n / total) * 100) : 0);
const statusOf = (err: unknown) => (axios.isAxiosError(err) ? err.response?.status : undefined);

type AutoState = {
  round: number;
  currentStep: number;
  interval: string;
  symbolIndex: number;
  totalSymbols: number;
  currentSymbol: string;
  phase: 'fetching' | 'cooldown';
  cooldownUntil: number;
  failedSymbols: string[];
  logs: string[];
};

function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="mb-1.5 block text-sm font-medium text-foreground">{children}</span>;
}

// Server log lines; the box follows new lines by its own scroll (never the page).
function LogBox({ logs, lineClass }: { logs: string[]; lineClass: (line: string) => string }) {
  const { ref, onScroll } = useStickToBottom(logs);
  return (
    <div ref={ref} onScroll={onScroll}
      className="max-h-[250px] space-y-1 overflow-y-auto rounded-xl border border-separator bg-surface-secondary p-3 font-mono text-[11px] leading-snug text-foreground/80">
      {logs.map((line, i) => <div key={i} className={`break-words ${lineClass(line)}`}>{line}</div>)}
    </div>
  );
}

export function DashboardView() {
  const t = useT(dashboard);
  const tc = useT(common);

  const [watchlists, setWatchlists] = useState<Record<string, WatchItem[]>>({});
  const [selectedWatchlist, setSelectedWatchlist] = useState(ALL);
  const [selectedCombineWatchlists, setSelectedCombineWatchlists] = useState<string[]>([]);
  const [tvMode, setTvMode] = useState<number>(3);
  const [savingTvMode, setSavingTvMode] = useState(false);
  const [autoSkipMinutes, setAutoSkipMinutes] = useState<number>(15);
  const [savingAutoSkip, setSavingAutoSkip] = useState(false);

  // Initial settings and watchlists, loaded in parallel.
  useEffect(() => {
    void (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/watchlist`);
        setWatchlists(res.data);
      } catch (e) {
        console.error('Failed to fetch watchlists', e);
      }
    })();
    void (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/settings/tv_mode`);
        if (typeof res.data?.mode === 'number') setTvMode(res.data.mode);
      } catch { /* fallback is 3 */ }
    })();
    void (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/settings/auto_skip_minutes`);
        if (typeof res.data?.minutes === 'number') setAutoSkipMinutes(res.data.minutes);
      } catch { /* fallback is 15 */ }
    })();
  }, []);

  const handleAutoSkipChange = async (minutes: number) => {
    if (isNaN(minutes) || minutes < 1 || minutes > 100) {
      setAutoSkipMinutes(minutes);
      return;
    }
    const prev = autoSkipMinutes;
    setAutoSkipMinutes(minutes); // optimistic
    setSavingAutoSkip(true);
    try {
      await axios.post(`${API_BASE}/api/settings/auto_skip_minutes`, { minutes });
    } catch (err) {
      console.error('Failed to save auto skip minutes', err);
      setAutoSkipMinutes(prev); // revert
      notify.error(t('saveAutoSkipFailed'));
    } finally {
      setSavingAutoSkip(false);
    }
  };

  const handleTvModeChange = async (mode: number) => {
    const prev = tvMode;
    setTvMode(mode); // optimistic
    setSavingTvMode(true);
    try {
      await axios.post(`${API_BASE}/api/settings/tv_mode`, { mode });
    } catch (err) {
      console.error('Failed to save TV mode', err);
      setTvMode(prev); // revert
      notify.error(t('saveTvModeFailed'));
    } finally {
      setSavingTvMode(false);
    }
  };

  const getCombinedSymbols = () => {
    if (selectedCombineWatchlists.length === 0) return SYMBOLS;
    const combinedSet = new Set<string>();
    selectedCombineWatchlists.forEach((name) => {
      (watchlists[name] || []).forEach((item) => combinedSet.add(item.symbol));
    });
    return SYMBOLS.filter((s) => combinedSet.has(s.symbol));
  };

  const [symbol, setSymbol] = useState('BTCUSDT');
  const [exchange, setExchange] = useState('BINANCE');
  const [interval, setInterval] = useState('4h');
  const [extendedSession, setExtendedSession] = useState(false);
  const [rows, setRows] = useState(80);
  // CSV mode: false = default (only the TFs whose bar just closed) · true = legacy (all 4 TFs every
  // round). Legacy is needed right after adding a symbol, which has no 1d/1w bars in the DB yet.
  const [forceAllTf, setForceAllTf] = useState(false);
  const [data, setData] = useState<TradeData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<FetchError | null>(null);

  const [isAutomating, setIsAutomating] = useState(false);
  const [automateProgress, setAutomateProgress] = useState(EMPTY_PROGRESS);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [completedSummary, setCompletedSummary] = useState<{ interval: string; extendedSession: boolean; failedSymbols: string[] } | null>(null);

  // Automate All (custom server job)
  const [showAutomateModal, setShowAutomateModal] = useState(false);
  const [automateCustomTFs, setAutomateCustomTFs] = useState<Record<string, boolean>>({ '1h': false, '4h': false, '1d': false, '1w': false });
  const [automateCustomExt, setAutomateCustomExt] = useState(false);

  // Blocking "working" dialog while a start/stop command is sent.
  const [busyKey, setBusyKey] = useState<DashKey | null>(null);
  const runWithLoading = async (key: DashKey, action: () => Promise<void>) => {
    setBusyKey(key);
    try {
      await action();
    } finally {
      setBusyKey(null);
    }
  };

  // TradingView connection test
  const [connTesting, setConnTesting] = useState(false);
  const [connTest, setConnTest] = useState<ConnTestResult | null>(null);
  const [connApiError, setConnApiError] = useState(false);
  const [showConnTestModal, setShowConnTestModal] = useState(false);

  const runConnTest = async () => {
    setConnTesting(true);
    setConnTest(null);
    setConnApiError(false);
    setShowConnTestModal(true);
    try {
      const res = await axios.post<ConnTestResult>(`${API_BASE}/api/tv/test`, {}, { timeout: 120000 });
      setConnTest(res.data);
    } catch (err) {
      console.error('conn test failed', err);
      setConnApiError(true);
      setConnTest({ ok: false, verdict: '', verdict_level: 'error', passed: 0, total: 0, duration: 0, logs: [] });
    } finally {
      setConnTesting(false);
    }
  };

  // Auto Automate All loop, driven by the server job status.
  const [isAutoAutomating, setIsAutoAutomating] = useState(false);
  const [autoState, setAutoState] = useState<AutoState | null>(null);

  const lastRunRef = useRef<{ interval: string; extendedSession: boolean }>({ interval: '4h', extendedSession: false });
  const customRunningRef = useRef(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const [confirmKind, setConfirmKind] = useState<ConfirmKind | null>(null);

  const applyJob = useCallback((j: AutomateJob | null) => {
    if (!j || j.status === 'idle') {
      setIsAutoAutomating(false);
      setAutoState(null);
      setIsAutomating(false);
      setAutomateProgress(EMPTY_PROGRESS);
      return;
    }

    if (j.mode === 'auto' && j.status === 'running') {
      const stepIdx = Math.max(1, j.step_index);
      setIsAutoAutomating(true);
      setAutoState({
        round: j.round,
        currentStep: stepIdx,
        interval: j.current_tf || AUTO_STEPS[stepIdx - 1]?.interval || '',
        symbolIndex: j.current,
        totalSymbols: j.total || SYMBOLS.length,
        currentSymbol: j.current_symbol || '',
        phase: j.phase === 'cooldown' ? 'cooldown' : 'fetching',
        cooldownUntil: j.cooldown_until ? new Date(j.cooldown_until).getTime() : 0,
        failedSymbols: Array.from(new Set(j.failed.map(stripTf))),
        logs: j.logs || [],
      });
    } else {
      setIsAutoAutomating(false);
      setAutoState(null);
    }

    if (j.mode === 'custom') {
      if (j.status === 'running') {
        setIsAutomating(true);
        setAutomateProgress({ current: j.current, total: j.total || SYMBOLS.length, currentSymbol: j.current_symbol || '', logs: j.logs || [] });
      } else if (j.status === 'stopped') {
        setIsAutomating(false);
        setAutomateProgress(EMPTY_PROGRESS);
      } else if (customRunningRef.current) {
        customRunningRef.current = false;
        setIsAutomating(false);
        setCompletedSummary({
          interval: lastRunRef.current.interval,
          extendedSession: lastRunRef.current.extendedSession,
          failedSymbols: Array.from(new Set(j.failed.map(stripTf))),
        });
        setShowSuccessModal(true);
      } else if (j.status === 'done') {
        setIsAutomating(false);
        setAutomateProgress(EMPTY_PROGRESS);
      }
    }
  }, []);

  const pollStatus = useCallback(() => {
    clearTimeout(pollRef.current);
    const tick = async () => {
      try {
        const res = await axios.get<AutomateJob>(`${API_BASE}/api/automate/status`);
        applyJob(res.data);
        if (res.data?.status === 'running') pollRef.current = setTimeout(tick, 3000);
      } catch { /* ignore transient polling errors */ }
    };
    void tick();
  }, [applyJob]);

  useEffect(() => {
    pollStatus();
    return () => clearTimeout(pollRef.current);
  }, [pollStatus]);

  const startAutoAutomateExecute = async () => {
    const targets = selectedCombineWatchlists.length > 0
      ? getCombinedSymbols()
      : (selectedWatchlist !== ALL && watchlists[selectedWatchlist]
        ? allSymbols().filter((s) => watchlists[selectedWatchlist].map((w) => w.symbol).includes(s.symbol))
        : allSymbols());

    await runWithLoading('busyStartAuto', async () => {
      try {
        await axios.post(`${API_BASE}/api/auto/start`, {
          symbols: targets.map((s) => ({ symbol: s.symbol, exchange: s.exchange })),
          rows,
          force_all_tf: forceAllTf,
        });
        setIsAutoAutomating(true);
        pollStatus();
      } catch (err) {
        if (statusOf(err) === 409) notify.warning(t('jobBusy'));
        else { console.error('start auto failed', err); notify.error(t('startAutoFailed')); }
      }
    });
  };

  const stopAutoAutomateExecute = async () => {
    await runWithLoading('busyStopAuto', async () => {
      try {
        await axios.post(`${API_BASE}/api/auto/stop`);
      } catch (err) {
        console.error('stop auto failed', err);
      }
      pollStatus();
    });
  };

  const stopCustomExecute = () => runWithLoading('busyStopCustom', async () => {
    try {
      await axios.post(`${API_BASE}/api/auto/stop`);
      setIsAutomating(false);
      customRunningRef.current = false;
      setAutomateProgress(EMPTY_PROGRESS);
    } catch (err) {
      console.error('stop automate failed', err);
    }
    pollStatus();
  });

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/api/data`, {
        symbol,
        exchange,
        interval,
        extended_session: extendedSession,
        rows,
      });
      setData([...response.data].reverse());
    } catch (err) {
      const res = axios.isAxiosError(err) ? err.response : undefined;
      console.error('Backend Error Response:', res?.data || (err as Error)?.message);
      if (res) {
        const detail = res.data?.detail;
        setError(detail ? { detail: typeof detail === 'string' ? detail : JSON.stringify(detail) } : { key: 'fetchFailed' });
      } else {
        setError({ key: 'noServer' });
      }
    } finally {
      setLoading(false);
    }
  };

  const startCustomRun = async (targets: Target[], itvs: string[], ext: boolean) => {
    lastRunRef.current = { interval: itvs[0], extendedSession: ext };
    customRunningRef.current = true;
    setError(null);
    setIsAutomating(true);
    setAutomateProgress({ current: 0, total: targets.length, currentSymbol: '', logs: [] });
    setShowAutomateModal(false);
    await runWithLoading('busyStartCustom', async () => {
      try {
        await axios.post(`${API_BASE}/api/automate`, {
          timeframes: itvs,
          symbols: targets.map((s) => ({ symbol: s.symbol, exchange: s.exchange })),
          extended_session: ext,
          rows,
        });
        pollStatus();
      } catch (err) {
        customRunningRef.current = false;
        setIsAutomating(false);
        if (statusOf(err) === 409) notify.warning(t('jobBusy'));
        else { console.error('start automate failed', err); notify.error(t('startCustomFailed')); }
      }
    });
  };

  const startAutomateExecute = () => {
    let targets = SYMBOLS;
    if (selectedCombineWatchlists.length > 0) {
      targets = getCombinedSymbols();
    } else if (selectedWatchlist !== ALL && watchlists[selectedWatchlist]) {
      const symbolsInList = watchlists[selectedWatchlist].map((s) => s.symbol);
      targets = SYMBOLS.filter((s) => symbolsInList.includes(s.symbol));
    }
    const tfs = CUSTOM_TFS.filter((tf) => automateCustomTFs[tf]);
    if (tfs.length === 0) {
      notify.warning(t('pickTf'));
      return;
    }
    void startCustomRun(targets, tfs, automateCustomExt);
  };

  const retryFailedExecute = (symbolNames: string[]) => {
    const targets = SYMBOLS.filter((s) => symbolNames.includes(s.symbol));
    if (targets.length === 0) return;
    void startCustomRun(targets, [lastRunRef.current.interval], lastRunRef.current.extendedSession);
  };

  const selectAllCustomTFs = (val: boolean) => setAutomateCustomTFs({ '1h': val, '4h': val, '1d': val, '1w': val });

  // Texts of the open confirmation, built at render so a language switch updates them.
  const confirmConfig = confirmKind === 'startAuto' ? {
    title: t('startAutoTitle'),
    message: [t('startAutoBody'), forceAllTf ? t('startAutoLegacy') : t('startAutoDefault'), t('startAutoNote')].join('\n\n'),
    confirmText: t('startAutoConfirm'), cancelText: undefined, type: 'success' as const, onConfirm: startAutoAutomateExecute,
  } : confirmKind === 'stopAuto' ? {
    title: t('stopAutoTitle'), message: t('stopAutoBody'),
    confirmText: t('stopConfirm'), cancelText: t('keepRunning'), type: 'danger' as const, onConfirm: stopAutoAutomateExecute,
  } : {
    title: t('stopCustomTitle'), message: t('stopCustomBody'),
    confirmText: t('stopConfirm'), cancelText: t('keepRunning'), type: 'danger' as const, onConfirm: stopCustomExecute,
  };

  const watchlistNames = Object.keys(watchlists);
  const combineLabel = selectedCombineWatchlists.length === 0
    ? t('combinePlaceholder')
    : t('combineSelected', { n: selectedCombineWatchlists.length, names: selectedCombineWatchlists.join(', ') });
  const busy = loading || isAutomating || isAutoAutomating;

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <Card.Header>
          <SectionHeader icon={CloudDownload} tint="bg-sky-500/15 text-sky-600 dark:text-sky-400"
            title={t('fetchTitle')} description={t('fetchDesc')} />
        </Card.Header>
        <Card.Content className="space-y-6">
          <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-12">
            <div className="w-full lg:col-span-4">
              <FieldLabel>{t('symbol')}</FieldLabel>
              <Autocomplete
                value={symbol}
                onChange={setSymbol}
                options={SYMBOLS}
                placeholder={t('symbolPlaceholder')}
                valueKey="symbol"
                labelKey="name"
                onSelectOption={(opt) => { if (opt.exchange) setExchange(opt.exchange); }}
              />
            </div>
            <div className="w-full lg:col-span-3">
              <FieldLabel>{t('exchange')}</FieldLabel>
              <Autocomplete value={exchange} onChange={setExchange} options={EXCHANGES} placeholder={t('exchangePlaceholder')} />
            </div>
            <Select className="w-full lg:col-span-2" value={interval} isDisabled={isAutoAutomating}
              onChange={(k) => { if (k !== null) setInterval(String(k)); }}>
              <Label>{t('interval')}</Label>
              <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
              <Select.Popover>
                <ListBox>
                  {INTERVALS.map((iv) => (
                    <ListBox.Item key={iv} id={iv} textValue={iv}>{iv}<ListBox.ItemIndicator /></ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
            <TextField className="w-full lg:col-span-2" type="number" value={String(rows)} isDisabled={isAutoAutomating}
              onChange={(v) => setRows(Number(v))}>
              <Label>{t('rows')}</Label>
              <Input min={10} max={1000} className="font-mono" />
            </TextField>
            <div className="flex h-10 items-center lg:col-span-1">
              <Checkbox isSelected={extendedSession} onChange={setExtendedSession} isDisabled={isAutoAutomating}>
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  <span className="whitespace-nowrap text-sm">{t('extend')}</span>
                </Checkbox.Content>
              </Checkbox>
            </div>
          </div>

          <div className="space-y-4 border-t border-separator pt-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted">
              <SlidersHorizontal className="size-4" />{t('settingsTitle')}
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Select className="w-full" value={String(tvMode)} isDisabled={savingTvMode}
                onChange={(k) => { if (k !== null) void handleTvModeChange(Number(k)); }}>
                <Label>{t('tvMode')}</Label>
                <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
                <Select.Popover>
                  <ListBox>
                    {TV_MODES.map((m) => (
                      <ListBox.Item key={m.id} id={m.id} textValue={t(m.label)}>{t(m.label)}<ListBox.ItemIndicator /></ListBox.Item>
                    ))}
                  </ListBox>
                </Select.Popover>
              </Select>
              <TextField className="w-full" type="number" value={String(autoSkipMinutes)} isDisabled={savingAutoSkip}
                onChange={(v) => void handleAutoSkipChange(Number(v))}>
                <Label>{t('autoSkip')}</Label>
                <Input min={1} max={100} placeholder="15" className="font-mono" />
                <Description>{t('autoSkipHelp')}</Description>
              </TextField>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 border-t border-separator pt-5 md:grid-cols-2">
            <Select className="w-full" value={selectedWatchlist}
              onChange={(k) => { if (k !== null) setSelectedWatchlist(String(k)); }}>
              <Label>{t('activeWatchlist')}</Label>
              <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
              <Description>{t('activeWatchlistHelp')}</Description>
              <Select.Popover>
                <ListBox>
                  <ListBox.Item id={ALL} textValue={t('allSymbols')}>{t('allSymbols')}<ListBox.ItemIndicator /></ListBox.Item>
                  {watchlistNames.map((name) => (
                    <ListBox.Item key={name} id={name} textValue={name}>{name}<ListBox.ItemIndicator /></ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
            <div className="space-y-1">
              <Select className="w-full" selectionMode="multiple" value={selectedCombineWatchlists}
                onChange={(keys) => setSelectedCombineWatchlists(((keys as Key[] | null) ?? []).map(String))}>
                <Label>{t('combine')}</Label>
                <Select.Trigger>
                  <span className={`min-w-0 flex-1 truncate text-left ${selectedCombineWatchlists.length ? '' : 'text-muted'}`}>{combineLabel}</span>
                  <Select.Indicator />
                </Select.Trigger>
                <Description>{t('combineHelp')}</Description>
                <Select.Popover>
                  <ListBox selectionMode="multiple" renderEmptyState={() => (
                    <div className="py-3 text-center text-xs text-muted">{t('combineEmpty')}</div>
                  )}>
                    {watchlistNames.map((name) => (
                      <ListBox.Item key={name} id={name} textValue={name}>
                        <span className="truncate font-medium">{name}</span>
                        <span className="ml-auto pl-2 text-xs text-muted">{t('listCount', { n: watchlists[name]?.length || 0 })}</span>
                        <ListBox.ItemIndicator />
                      </ListBox.Item>
                    ))}
                  </ListBox>
                </Select.Popover>
              </Select>
              {selectedCombineWatchlists.length > 0 ? (
                <Button size="sm" variant="ghost" className="text-danger" onPress={() => setSelectedCombineWatchlists([])}>
                  {t('combineClear')}
                </Button>
              ) : null}
            </div>
          </div>
        </Card.Content>
        <Card.Footer className="flex flex-wrap items-center justify-center gap-3 border-t border-separator pt-5 sm:justify-end">
          <Button className="w-full sm:w-auto" onPress={fetchData} isPending={loading} isDisabled={busy}>
            {loading ? <Spinner size="sm" color="current" /> : <Database className="size-4" />}
            {t('fetchNow')}
          </Button>
          {isAutomating ? (
            <div className="flex w-full gap-2 sm:w-auto">
              <Button className="flex-1 sm:flex-none" variant="secondary" isDisabled>
                <Spinner size="sm" color="current" />
                <span className="font-mono">{automateProgress.current}/{automateProgress.total}</span>
              </Button>
              <Button variant="danger" onPress={() => setConfirmKind('stopCustom')}>
                <Square className="size-4" />{t('stop')}
              </Button>
            </div>
          ) : (
            <Button className="w-full sm:w-auto" variant="secondary" isDisabled={loading || isAutoAutomating}
              onPress={() => setShowAutomateModal(true)}>
              <Layers className="size-4" />{t('automateAll')}
            </Button>
          )}
          {isAutoAutomating ? (
            <Button className="w-full animate-pulse sm:w-auto" variant="danger" onPress={() => setConfirmKind('stopAuto')}>
              <Square className="size-4" />{t('stopAuto')}
            </Button>
          ) : (
            <>
              <div className={`flex h-10 items-center gap-2 rounded-xl border px-3 ${forceAllTf ? 'border-warning/50 bg-warning-soft' : 'border-separator bg-surface-secondary'}`}>
                <Checkbox isSelected={forceAllTf} onChange={setForceAllTf} isDisabled={busy}>
                  <Checkbox.Content>
                    <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                    <span className={`text-sm font-medium ${forceAllTf ? 'text-warning-soft-foreground' : 'text-muted'}`}>
                      {forceAllTf ? t('csvLegacy') : t('csvDefault')}
                    </span>
                  </Checkbox.Content>
                </Checkbox>
                <Tooltip delay={200}>
                  <Tooltip.Trigger aria-label={t('csvHelp')}>
                    <Info className="size-4 text-muted" />
                  </Tooltip.Trigger>
                  <Tooltip.Content className="max-w-xs text-xs">{t('csvHelp')}</Tooltip.Content>
                </Tooltip>
              </div>
              <Button className="w-full sm:w-auto" variant="secondary" isDisabled={loading || isAutomating}
                onPress={() => setConfirmKind('startAuto')}>
                <Repeat className="size-4" />{t('autoAll')}
              </Button>
            </>
          )}
          <Button className="w-full sm:w-auto" variant="tertiary" onPress={runConnTest} isPending={connTesting}>
            {connTesting ? <Spinner size="sm" color="current" /> : <Activity className="size-4" />}
            {t('connTest')}
          </Button>
        </Card.Footer>
      </Card>

      {isAutoAutomating && autoState && (
        <Card className="rounded-2xl border border-success/30">
          <Card.Header>
            <SectionHeader icon={Repeat} tint="bg-success-soft text-success"
              title={(
                <span className="flex items-center gap-2">
                  <span className="relative flex size-2.5">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex size-2.5 rounded-full bg-success" />
                  </span>
                  {t('autoRunning', { round: autoState.round })}
                </span>
              )}
              actions={(
                <Chip size="sm" variant="soft" color={autoState.phase === 'cooldown' ? 'warning' : 'success'}>
                  {autoState.phase === 'cooldown' ? t('phaseCooldown') : t('phaseFetching')}
                </Chip>
              )} />
          </Card.Header>
          <Card.Content className="space-y-4">
            {autoState.phase === 'cooldown' ? (
              <div className="flex flex-col items-center justify-center space-y-3 py-4 text-center">
                <div className="flex items-center gap-2 text-4xl font-extrabold tracking-wider text-foreground">
                  <Timer className="size-7 text-warning" />
                  <Countdown until={autoState.cooldownUntil} />
                </div>
                <p className="text-sm text-muted">
                  {t('cooldownBody', { round: autoState.round })}<br />
                  {t('cooldownNext', { next: autoState.round + 1 })}
                </p>
                {autoState.failedSymbols.length > 0 && (
                  <Alert status="danger" className="w-full text-left">
                    <Alert.Indicator />
                    <Alert.Content>
                      <Alert.Title>{t('failedRound', { n: autoState.failedSymbols.length })}</Alert.Title>
                      <Alert.Description className="break-words font-mono text-xs">{autoState.failedSymbols.join(', ')}</Alert.Description>
                    </Alert.Content>
                    <Button size="sm" variant="danger" isDisabled={isAutomating} onPress={() => retryFailedExecute(autoState.failedSymbols)}>
                      <RefreshCw className="size-3.5" />{t('retryFailed', { n: autoState.failedSymbols.length })}
                    </Button>
                  </Alert>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-separator bg-surface-secondary p-3">
                    <span className="block text-xs text-muted">{t('stepInRound')}</span>
                    <span className="text-base font-bold">
                      <span className="font-mono">{autoState.currentStep} / {AUTO_STEPS.length}</span>
                      {AUTO_STEPS[autoState.currentStep - 1] ? ` (${t(AUTO_STEPS[autoState.currentStep - 1].label)})` : ''}
                    </span>
                  </div>
                  <div className="rounded-xl border border-separator bg-surface-secondary p-3">
                    <span className="block text-xs text-muted">{t('currentSymbol')}</span>
                    <span className="animate-pulse font-mono text-base font-bold text-accent">{autoState.currentSymbol || '-'}</span>
                  </div>
                  <div className="rounded-xl border border-separator bg-surface-secondary p-3">
                    <span className="block text-xs text-muted">{t('stepProgress')}</span>
                    <span className="font-mono text-base font-bold">
                      {autoState.symbolIndex} / {autoState.totalSymbols} ({pct(autoState.symbolIndex, autoState.totalSymbols)}%)
                    </span>
                  </div>
                </div>
                <ProgressBar aria-label={t('stepProgress')} value={pct(autoState.symbolIndex, autoState.totalSymbols)} color="success" size="sm">
                  <ProgressBar.Track><ProgressBar.Fill /></ProgressBar.Track>
                </ProgressBar>
                {autoState.failedSymbols.length > 0 && (
                  <Alert status="danger">
                    <Alert.Indicator />
                    <Alert.Content>
                      <Alert.Title>{t('failedCount', { n: autoState.failedSymbols.length })}</Alert.Title>
                      <Alert.Description className="break-words font-mono text-xs">{autoState.failedSymbols.join(', ')}</Alert.Description>
                    </Alert.Content>
                  </Alert>
                )}
              </div>
            )}
            {autoState.logs && autoState.logs.length > 0 && (
              <LogBox logs={autoState.logs}
                lineClass={(log) => (log.includes('failed') ? 'font-semibold text-danger' : '')} />
            )}
          </Card.Content>
        </Card>
      )}

      {isAutomating && (
        <Card className="rounded-2xl border border-accent/30">
          <Card.Content className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-2 text-sm font-semibold text-accent">
                <Spinner size="sm" color="current" />
                {t('customRunning', { symbol: automateProgress.currentSymbol })}
              </span>
              <span className="font-mono text-sm font-bold">
                {automateProgress.current} / {automateProgress.total} ({pct(automateProgress.current, automateProgress.total)}%)
              </span>
            </div>
            <ProgressBar aria-label={t('customProgress')} value={pct(automateProgress.current, automateProgress.total)} color="accent">
              <ProgressBar.Track><ProgressBar.Fill /></ProgressBar.Track>
            </ProgressBar>
            {automateProgress.logs.length > 0 && (
              <LogBox logs={automateProgress.logs}
                lineClass={(log) => (log.includes('Error') || log.includes('Timeout') ? 'text-danger'
                  : log.includes('Exhausted') ? 'text-warning' : 'text-accent')} />
            )}
          </Card.Content>
        </Card>
      )}

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>{t('errorTitle')}</Alert.Title>
            <Alert.Description>{error.detail ?? (error.key ? t(error.key) : '')}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      {data.length > 0 ? (
        <ResultTable data={data} />
      ) : (
        !loading && !error && (
          <Card className="rounded-2xl">
            <Card.Content className="flex flex-col items-center gap-2 py-12 text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-surface-secondary text-muted"><Inbox className="size-6" /></span>
              <p className="font-medium">{t('emptyTitle')}</p>
              <p className="text-sm text-muted">{t('emptyBody')}</p>
            </Card.Content>
          </Card>
        )
      )}

      <ConfirmationModal
        isOpen={confirmKind !== null}
        title={confirmConfig.title}
        message={confirmConfig.message}
        confirmText={confirmConfig.confirmText}
        cancelText={confirmConfig.cancelText}
        type={confirmConfig.type}
        onConfirm={() => { void confirmConfig.onConfirm(); }}
        onCancel={() => setConfirmKind(null)}
      />

      {/* Automate All: pick timeframes */}
      <Modal.Backdrop isOpen={showAutomateModal} onOpenChange={setShowAutomateModal}>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[480px]">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon className="bg-accent-soft text-accent-soft-foreground"><Layers className="size-5" /></Modal.Icon>
              <Modal.Heading>{t('automateTitle')}</Modal.Heading>
            </Modal.Header>
            <Modal.Body className="space-y-5">
              <p className="text-sm text-muted">
                {t('automateTarget', {
                  target: selectedWatchlist !== ALL ? t('automateTargetList', { name: selectedWatchlist }) : t('automateTargetAll'),
                })}
              </p>
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{t('pickTimeframe')}</span>
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onPress={() => selectAllCustomTFs(true)}>{t('selectAll')}</Button>
                    <Button size="sm" variant="tertiary" onPress={() => selectAllCustomTFs(false)}>{t('deselectAll')}</Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-4">
                  {CUSTOM_TFS.map((tf) => (
                    <Checkbox key={tf} isSelected={automateCustomTFs[tf]}
                      onChange={(on: boolean) => setAutomateCustomTFs((prev) => ({ ...prev, [tf]: on }))}>
                      <Checkbox.Content>
                        <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                        <span className="font-mono font-medium uppercase">{tf}</span>
                      </Checkbox.Content>
                    </Checkbox>
                  ))}
                </div>
              </div>
              <Checkbox isSelected={automateCustomExt} onChange={setAutomateCustomExt}>
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  <span className="text-sm">{t('automateExt')}</span>
                </Checkbox.Content>
              </Checkbox>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="tertiary" slot="close">{tc('cancel')}</Button>
              <Button onPress={startAutomateExecute}><CloudDownload className="size-4" />{t('automateStart')}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>

      {/* Custom job finished */}
      <Modal.Backdrop isOpen={showSuccessModal && completedSummary !== null}
        onOpenChange={(open) => { if (!open) { setShowSuccessModal(false); setCompletedSummary(null); } }}>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[460px]">
            <Modal.Header>
              <Modal.Icon className="bg-success-soft text-success"><CheckCircle2 className="size-5" /></Modal.Icon>
              <Modal.Heading>{t('doneTitle')}</Modal.Heading>
            </Modal.Header>
            {completedSummary ? (
              <Modal.Body className="space-y-4">
                <p className="text-sm text-muted">{t('doneBody')}</p>
                <div className="space-y-2 rounded-xl border border-separator bg-surface-secondary p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted">{t('doneDetails')}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-surface p-3">
                      <span className="block text-[11px] font-semibold text-muted">{t('doneInterval')}</span>
                      <span className="mt-0.5 block text-sm font-bold">
                        {TF_LABEL[completedSummary.interval] ? t(TF_LABEL[completedSummary.interval]) : completedSummary.interval}
                      </span>
                    </div>
                    <div className="rounded-lg bg-surface p-3">
                      <span className="block text-[11px] font-semibold text-muted">{t('doneExt')}</span>
                      <span className={`mt-0.5 block text-sm font-bold ${completedSummary.extendedSession ? 'text-success' : 'text-muted'}`}>
                        {completedSummary.extendedSession ? t('yes') : t('no')}
                      </span>
                    </div>
                  </div>
                </div>
                {completedSummary.failedSymbols.length > 0 && (
                  <Alert status="danger">
                    <Alert.Indicator />
                    <Alert.Content>
                      <Alert.Title>{t('doneFailed', { n: completedSummary.failedSymbols.length })}</Alert.Title>
                      <Alert.Description className="break-words font-mono text-xs">{completedSummary.failedSymbols.join(', ')}</Alert.Description>
                    </Alert.Content>
                  </Alert>
                )}
              </Modal.Body>
            ) : null}
            <Modal.Footer>
              {completedSummary && completedSummary.failedSymbols.length > 0 && (
                <Button variant="danger" onPress={() => {
                  const toRetry = completedSummary.failedSymbols;
                  setShowSuccessModal(false);
                  setCompletedSummary(null);
                  retryFailedExecute(toRetry);
                }}>
                  <RefreshCw className="size-4" />{t('retryFailed', { n: completedSummary.failedSymbols.length })}
                </Button>
              )}
              <Button onPress={() => { setShowSuccessModal(false); setCompletedSummary(null); }}>{t('doneOk')}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>

      {/* TradingView connection test */}
      <Modal.Backdrop isOpen={showConnTestModal} isDismissable={!connTesting} isKeyboardDismissDisabled={connTesting}
        onOpenChange={(open) => { if (!open && !connTesting) setShowConnTestModal(false); }}>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[560px]">
            {!connTesting ? <Modal.CloseTrigger /> : null}
            <Modal.Header>
              <Modal.Icon className="bg-accent-soft text-accent-soft-foreground"><Activity className="size-5" /></Modal.Icon>
              <Modal.Heading>{t('connTitle')}</Modal.Heading>
            </Modal.Header>
            <Modal.Body className="space-y-3">
              {connTesting ? (
                <div className="flex flex-col items-center justify-center space-y-3 py-10 text-center">
                  <Spinner size="lg" />
                  <p className="text-sm text-muted">{t('connTesting')}</p>
                </div>
              ) : connTest && (
                <>
                  <div className={`rounded-xl px-4 py-3 text-sm font-semibold ${connLevelClasses[connTest.verdict_level] ?? connLevelClasses.info}`}>
                    {connApiError ? t('connApiFailed') : connTest.verdict}
                    {connTest.total > 0 && (
                      <span className="mt-1 block text-xs font-normal opacity-80">
                        {t('connPassed', { passed: connTest.passed, total: connTest.total, sec: connTest.duration })}
                      </span>
                    )}
                  </div>
                  {connTest.logs.length > 0 && (
                    <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
                      {connTest.logs.map((l, i) => (
                        <div key={i} className={`flex items-start gap-2 rounded-lg px-3 py-2 text-xs ${connLevelClasses[l.level] ?? connLevelClasses.info}`}>
                          <span className="shrink-0 font-mono opacity-70">{l.time}</span>
                          <span className="min-w-0 break-words font-medium">{l.message}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Modal.Body>
            {!connTesting && connTest ? (
              <Modal.Footer>
                <Button variant="secondary" onPress={runConnTest}><RefreshCw className="size-4" />{t('connRetry')}</Button>
                <Button variant="tertiary" slot="close">{tc('close')}</Button>
              </Modal.Footer>
            ) : null}
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>

      {/* Blocking "working" dialog while a command is sent */}
      <Modal.Backdrop isOpen={busyKey !== null} isDismissable={false} isKeyboardDismissDisabled>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[380px]">
            <Modal.Body className="flex flex-col items-center space-y-4 py-6 text-center">
              <span className="grid size-14 place-items-center rounded-2xl bg-accent-soft"><Spinner size="lg" /></span>
              <div className="space-y-1">
                <Modal.Heading>{t('busyTitle')}</Modal.Heading>
                <p className="text-sm font-semibold text-muted">{busyKey ? t(busyKey) : ''}</p>
              </div>
              <p className="text-xs text-muted">{t('busyHint')}</p>
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </div>
  );
}
