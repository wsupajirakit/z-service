import { Alert, Button, Card, Label, ListBox, Select, Spinner, Switch, Tooltip } from '@heroui/react';
import axios from 'axios';
import { Coins, Download, FolderOpen, Mountain, RefreshCw, Sparkles, Square, Timer, TrendingUp, Zap, type LucideIcon } from 'lucide-react';
import { useEffect, useEffectEvent, useState } from 'react';
import { notify } from '../components/notify';
import { useLang, useT, type MessageKey } from '../i18n';
import { gold } from '../i18n/messages/gold';
import { API_BASE, renderMarkdown, type GoldAnalysis, type GoldModel, type GoldSource } from '../lib';

type GoldKey = MessageKey<typeof gold>;
// A failure is either one of our own messages (translated at render) or the server's text.
type GoldError = { key: GoldKey } | { text: string };
type GoldStatus = { status?: string; started_at?: string; result?: GoldAnalysis; folder_link?: string; message?: string };

const EXPORT_MODES: {
  mode: string; label: GoldKey; desc: GoldKey; tfs: string; icon: LucideIcon; card: string; tile: string; text: string;
}[] = [
  { mode: 'scalp', label: 'modeScalp', desc: 'descScalp', tfs: '5m · 15m', icon: Zap,
    card: 'border-rose-500/30 bg-rose-500/5 hover:bg-rose-500/10', tile: 'bg-rose-500 text-white', text: 'text-rose-700 dark:text-rose-300' },
  { mode: 'intraday', label: 'modeIntraday', desc: 'descIntraday', tfs: '15m · 1h', icon: Timer,
    card: 'border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10', tile: 'bg-amber-500 text-white', text: 'text-amber-700 dark:text-amber-300' },
  { mode: 'swing', label: 'modeSwing', desc: 'descSwing', tfs: '1h · 4h · 1d', icon: TrendingUp,
    card: 'border-sky-500/30 bg-sky-500/5 hover:bg-sky-500/10', tile: 'bg-sky-500 text-white', text: 'text-sky-700 dark:text-sky-300' },
  { mode: 'position', label: 'modePosition', desc: 'descPosition', tfs: '1d · 1w', icon: Mountain,
    card: 'border-violet-500/30 bg-violet-500/5 hover:bg-violet-500/10', tile: 'bg-violet-500 text-white', text: 'text-violet-700 dark:text-violet-300' },
];

async function getPrice(exchange: string): Promise<number | null> {
  const res = await axios.get(`${API_BASE}/api/gold/price?exchange=${exchange}`);
  return res.data?.price ?? null;
}

// Markdown from renderMarkdown carries fixed colours; these overrides keep it readable in both themes.
const MD_CLASS = 'text-sm leading-relaxed text-foreground [&_h2]:text-foreground [&_h4]:text-foreground [&_strong]:text-foreground [&_h3]:text-amber-600 dark:[&_h3]:text-amber-400';

export function GoldView() {
  const t = useT(gold);
  const lang = useLang();
  const locale = lang === 'th' ? 'th-TH' : 'en-US';
  const [sources, setSources] = useState<GoldSource[]>([]);
  const [models, setModels] = useState<GoldModel[]>([]);
  const [exchange, setExchange] = useState('OANDA');
  const [model, setModel] = useState('gemini-2.5-flash');
  const [timeframes, setTimeframes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<GoldError | null>(null);
  const [result, setResult] = useState<GoldAnalysis | null>(null);
  const [folderLink, setFolderLink] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<string | null>(null);

  const [realtimePrice, setRealtimePrice] = useState<number | null>(null);
  const [realtimeLoading, setRealtimeLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [dlMode, setDlMode] = useState<string | null>(null);

  // Gold trading data set per mode (standalone /api/gold/export, for analysis in an external AI).
  const downloadGoldZip = async (mode: string) => {
    setDlMode(mode);
    try {
      const res = await axios.get(`${API_BASE}/api/gold/export`, {
        params: { mode, exchange },
        responseType: 'blob',
        timeout: 120000,
      });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `gold_${mode}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('gold export failed', err);
      notify.error(t('exportFailed'));
    } finally {
      setDlMode(null);
    }
  };

  const fetchPrice = async (currExchange: string) => {
    setRealtimeLoading(true);
    try {
      setRealtimePrice(await getPrice(currExchange));
    } catch (err) {
      console.error('Failed to fetch real-time price', err);
    } finally {
      setRealtimeLoading(false);
    }
  };

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const price = await getPrice(exchange);
        if (alive) setRealtimePrice(price);
      } catch (err) {
        console.error('Failed to fetch real-time price', err);
      } finally {
        if (alive) setRealtimeLoading(false);
      }
    };
    void load();
    return () => { alive = false; };
  }, [exchange]);

  const tick = useEffectEvent(() => { void fetchPrice(exchange); });
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(tick, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  // Apply a status payload from /api/gold/status to local state.
  const applyStatus = (data: GoldStatus) => {
    setStartedAt(data?.started_at || null);
    if (data?.status === 'done') {
      if (data.result) setResult(data.result);
      setFolderLink(data.folder_link || null);
    } else if (data?.status === 'error') {
      setError(data.message ? { text: data.message } : { key: 'analyzeFailed' });
    }
  };

  // Poll the server job until it leaves the "running" state (resume-safe: works
  // even if this component just mounted onto an already-running job).
  const pollUntilDone = async () => {
    setLoading(true);
    try {
      for (let i = 0; i < 120; i++) {
        const s = await axios.get<GoldStatus>(`${API_BASE}/api/gold/status`);
        if (s.data?.status !== 'running') {
          applyStatus(s.data);
          return;
        }
        setStartedAt(s.data?.started_at || null);
        await new Promise((r) => setTimeout(r, 2000));
      }
      setError({ key: 'timeout' });
    } finally {
      setLoading(false);
    }
  };

  // Load config + Gemini models, then attach to any existing server job so a
  // page refresh shows the last result (or resumes watching a running job).
  const onStatus = useEffectEvent((data: GoldStatus) => {
    if (data?.status === 'running') {
      void pollUntilDone(); // resume watching
    } else if (data?.status && data.status !== 'idle') {
      applyStatus(data); // show last finished result
    }
  });
  useEffect(() => {
    const load = async () => {
      try {
        const [cfg, mdl] = await Promise.all([
          axios.get(`${API_BASE}/api/gold/config`),
          axios.get(`${API_BASE}/api/gold/models`),
        ]);
        setSources(cfg.data.sources || []);
        setTimeframes(cfg.data.timeframes || []);
        if (cfg.data.default_model) setModel(cfg.data.default_model);
        setModels(mdl.data.models || []);
      } catch (e) {
        console.error('gold config load failed', e);
      }
      try {
        const s = await axios.get<GoldStatus>(`${API_BASE}/api/gold/status`);
        onStatus(s.data);
      } catch { /* ignore */ }
    };
    void load();
  }, []);

  const stopAnalysis = async () => {
    try {
      // The backend job fails and the polling loop resolves.
      await axios.post(`${API_BASE}/api/gold/automate/stop`);
    } catch (e) {
      console.error('Failed to stop analysis', e);
    }
  };

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setFolderLink(null);
    try {
      // Server-side job: runs Gemini, then uploads to Drive + notifies Telegram
      // per the destination settings. We poll status and show the result here too.
      await axios.post(`${API_BASE}/api/gold/automate`, { exchange, model, rows: 60 });
      await pollUntilDone();
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      // 409 = a job is already running: attach to it instead of failing.
      if (err?.response?.status === 409) {
        await pollUntilDone();
        return;
      }
      const text = err?.response?.data?.detail || err?.message;
      setError(text ? { text } : { key: 'analyzeFailed' });
    } finally {
      setLoading(false);
    }
  };

  const sourceItems = sources.length ? sources : [{ label: 'OANDA', exchange: 'OANDA' }];
  const modelItems = models.length ? models : [{ name: model, displayName: model }];

  const priceText = realtimePrice != null
    ? realtimePrice.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : null;

  return (
    <div className="space-y-6">
      {/* Live price: the page's headline */}
      <section className="relative overflow-hidden rounded-3xl border border-amber-500/30 bg-gradient-to-br from-amber-300/30 via-yellow-200/10 to-transparent p-6 shadow-sm dark:from-amber-500/20 dark:via-yellow-500/5 md:p-8">
        <Coins aria-hidden className="pointer-events-none absolute -right-6 -top-6 size-40 text-amber-500/10" />
        <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="relative flex size-2.5">
                <span className={`absolute inline-flex size-full rounded-full opacity-75 ${autoRefresh ? 'animate-ping bg-success' : 'bg-warning'}`} />
                <span className={`relative inline-flex size-2.5 rounded-full ${autoRefresh ? 'bg-success' : 'bg-warning'}`} />
              </span>
              <span className="text-xs font-semibold uppercase tracking-widest text-amber-800 dark:text-amber-300">{t('livePrice', { exchange })}</span>
            </div>
            <div className="flex items-baseline gap-2">
              {realtimeLoading && priceText == null ? (
                <span className="flex items-center gap-2 text-lg text-muted"><Spinner size="sm" />{t('loading')}</span>
              ) : priceText != null ? (
                <>
                  <span className="font-mono text-4xl font-bold tracking-tight text-amber-950 dark:text-amber-50 md:text-5xl">${priceText}</span>
                  <span className="text-sm font-medium text-amber-800/70 dark:text-amber-200/70">USD / oz</span>
                </>
              ) : (
                <span className="text-lg text-muted">{t('na')}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Tooltip delay={200}>
              <Button isIconOnly variant="secondary" aria-label={t('refreshPrice')} isDisabled={realtimeLoading}
                onPress={() => fetchPrice(exchange)} className="bg-background/70 backdrop-blur">
                <RefreshCw className={`size-4 ${realtimeLoading ? 'animate-spin' : ''}`} />
              </Button>
              <Tooltip.Content>{t('refreshPrice')}</Tooltip.Content>
            </Tooltip>
            <Switch isSelected={autoRefresh} onChange={setAutoRefresh} className="rounded-full bg-background/70 px-3 py-2 backdrop-blur">
              <Switch.Content>
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
                <span className="text-sm font-medium">{t('autoRun')}</span>
              </Switch.Content>
            </Switch>
          </div>
        </div>
      </section>

      {/* AI analysis */}
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-amber-400 to-yellow-500 text-white shadow-sm">
            <Sparkles className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('description', { tfs: timeframes.join(' · ') || '15m · 1h · 4h · 1d' })}</Card.Description>
          </div>
        </Card.Header>

        <Card.Content className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select fullWidth value={exchange} isDisabled={loading}
              onChange={(v) => { if (v != null) setExchange(String(v)); }}>
              <Label>{t('source')}</Label>
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Select.Popover>
                <ListBox>
                  {sourceItems.map((s) => (
                    <ListBox.Item key={s.exchange} id={s.exchange} textValue={`${s.label} — XAUUSD`}>
                      {s.label} — XAUUSD
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>

            <Select fullWidth value={model} isDisabled={loading}
              onChange={(v) => { if (v != null) setModel(String(v)); }}>
              <Label>{t('model')}</Label>
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Select.Popover>
                <ListBox>
                  {modelItems.map((m) => (
                    <ListBox.Item key={m.name} id={m.name} textValue={m.displayName}>
                      {m.displayName}
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
          </div>

          <div className="flex w-full gap-2">
            <Button fullWidth size="lg" onPress={analyze} isPending={loading}
              className="flex-1 bg-gradient-to-r from-amber-500 to-yellow-500 font-semibold text-amber-950 shadow-md shadow-amber-500/25 hover:from-amber-600 hover:to-yellow-500">
              {loading ? null : <Sparkles className="size-5" />}
              {loading ? t('analyzing') : t('analyze')}
            </Button>
            {loading && (
              <Button size="lg" variant="danger" onPress={stopAnalysis}><Square className="size-4" />{t('stop')}</Button>
            )}
          </div>

          {loading && (
            <Alert status="warning">
              <Alert.Indicator><Spinner size="sm" color="current" /></Alert.Indicator>
              <Alert.Content>
                <Alert.Description>
                  {t('runningOnServer', {
                    started: startedAt ? t('startedAt', { time: new Date(startedAt).toLocaleTimeString(locale) }) : '',
                  })}
                </Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          {error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{'key' in error ? t(error.key) : error.text}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
        </Card.Content>
      </Card>

      {/* Data set export: one card per trading style, each in its own colour */}
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400">
            <Download className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('exportTitle')}</Card.Title>
            <Card.Description>{t('exportBody')}</Card.Description>
            <p className="mt-1 text-xs text-muted">{t('exportHint')}</p>
          </div>
        </Card.Header>
        <Card.Content>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {EXPORT_MODES.map((b) => {
              const busy = dlMode === b.mode;
              return (
                <Button key={b.mode} variant="ghost" onPress={() => downloadGoldZip(b.mode)}
                  isDisabled={(dlMode !== null && !busy) || loading} aria-busy={busy || undefined}
                  className={`group h-auto flex-col items-start gap-3 rounded-2xl border p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-md ${b.card}`}>
                  <span className="flex w-full items-center justify-between">
                    <span className={`grid size-10 place-items-center rounded-xl shadow-sm ${b.tile}`}>
                      {busy ? <Spinner size="sm" color="current" /> : <b.icon className="size-5" />}
                    </span>
                    <span className="rounded-full bg-background/70 px-2 py-0.5 font-mono text-[11px] text-muted">{b.tfs}</span>
                  </span>
                  <span className="block">
                    <span className={`block text-base font-semibold ${b.text}`}>{t(b.label)}</span>
                    <span className="block text-xs font-normal text-muted">{t(b.desc)}</span>
                  </span>
                  <span className={`flex items-center gap-1.5 text-xs font-medium ${b.text}`}>
                    {busy ? t('fetching') : <><Download className="size-3.5" />{t('downloadZip')}</>}
                  </span>
                </Button>
              );
            })}
          </div>
        </Card.Content>
      </Card>

      {result && (
        <Card className="rounded-2xl">
          <Card.Header className="flex flex-row flex-wrap items-center gap-x-4 gap-y-1 border-b border-separator pb-4 text-sm text-muted">
            <span className="font-semibold text-foreground">{result.source_label} · XAUUSD</span>
            {result.latest_price != null && (
              <span>{t('latestPrice')}: <span className="font-mono font-semibold text-amber-700 dark:text-amber-400">{result.latest_price}</span></span>
            )}
            <span>{t('modelUsed')}: {result.model}</span>
            <span>{t('newsUsed')}: {result.news_count}</span>
            {folderLink && (
              <a href={folderLink} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1 font-medium text-accent hover:underline">
                <FolderOpen className="size-4" />{t('openDrive')}
              </a>
            )}
          </Card.Header>
          <Card.Content>
            <div className={MD_CLASS} dangerouslySetInnerHTML={{ __html: renderMarkdown(result.analysis) }} />
          </Card.Content>
          <Card.Footer className="border-t border-separator pt-3">
            <p className="text-xs text-muted">⚠️ {t('disclaimer')}</p>
          </Card.Footer>
        </Card>
      )}
    </div>
  );
}
