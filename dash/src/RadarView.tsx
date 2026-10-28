/**
 * Radar Summary — pick timeframes, compute a round, browse every past round.
 *
 * Two rules this page is built around:
 *  1. Every timestamp says WHICH clock it is on. Values arrive as offset-aware
 *     ISO strings and are rendered through Intl in ET or GMT+7 (one toggle,
 *     whole page), so DST is never assumed and nothing is stored pre-converted.
 *  2. A round that lacks a timeframe must never look like a complete one — it
 *     carries a PARTIAL badge and the server's warnings, everywhere it appears.
 *
 * All numbers come from the round document as computed by radar_engine (the
 * stock-radar formulas); this file only lays them out — it never recomputes.
 * Text the server sends (verdicts, glosses, warnings, clock labels) is shown as
 * it arrives; only this page's own words are translated.
 */
import {
  Alert, Button, Card, Checkbox, Chip, Description, Disclosure, Pagination, SearchField, Skeleton, Spinner,
  Table, ToggleButton, ToggleButtonGroup, Tooltip,
} from '@heroui/react';
import axios from 'axios';
import {
  AlertTriangle, Check, Clock, Download, Inbox, Play, Radar, RefreshCw, Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useConfirm } from './components/confirmContext';
import { errorDetail, notify } from './components/notify';
import { termGloss } from './digestTerms';
import { useLang, useT, type MessageKey } from './i18n';
import { common } from './i18n/messages/common';
import { radarSummary } from './i18n/messages/radarSummary';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
const TFS = ['1w', '1d', '4h', '1h'] as const;
type Tf = (typeof TFS)[number];
type Zone = 'ET' | 'TH';
type RKey = MessageKey<typeof radarSummary>;
type TFn = (key: RKey, vars?: Record<string, string | number>) => string;

const ZONE_TZ: Record<Zone, string> = { ET: 'America/New_York', TH: 'Asia/Bangkok' };
const ZONE_LABEL: Record<Zone, RKey> = { ET: 'zoneEt', TH: 'zoneTh' };

// ---------------------------------------------------------------- helpers --

/** Render an offset-aware ISO instant in the chosen zone. A value without an
 *  offset can't be converted, so it is shown as-is and flagged — never silently
 *  reinterpreted as some other timezone. */
function fmtTime(iso: string | null | undefined, zone: Zone, rawSuffix: string, withDate = true): string {
  if (!iso) return '—';
  const hasOffset = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(iso);
  // No offset = we cannot convert it. Show it as it was recorded and say so,
  // rather than silently pretending it is in the selected zone.
  if (!hasOffset || isNaN(d.getTime())) return `${String(iso).slice(0, 16)} ${rawSuffix}`;
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: ZONE_TZ[zone],
    ...(withDate ? { year: 'numeric', month: '2-digit', day: '2-digit' } : {}),
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d);
}

/** "3 h 12 min ago" — how stale a fetch is, at a glance. */
function ago(iso: string | null | undefined, t: TFn): string {
  if (!iso) return '';
  const ms = new Date(iso).getTime();
  if (isNaN(ms)) return '';
  const mins = Math.round((Date.now() - ms) / 60000);
  if (mins < 1) return t('justNow');
  if (mins < 60) return t('minsAgo', { m: mins });
  const h = Math.floor(mins / 60);
  if (h < 48) return t('hoursAgo', { h, m: mins % 60 });
  return t('daysAgo', { d: Math.floor(h / 24) });
}

/** Time and age formatters bound to the current language. */
function useFmt() {
  const t = useT(radarSummary);
  return {
    t,
    time: (iso: string | null | undefined, zone: Zone, withDate = true) => fmtTime(iso, zone, t('asRecorded'), withDate),
    ago: (iso: string | null | undefined) => ago(iso, t),
  };
}

/** Is this data old ENOUGH TO MISLEAD, as of right now? Measured against the
 *  clock rather than the round's stored age: a round is computed once but read
 *  for days, and re-running on unchanged data reuses it — so the stored age
 *  stops counting while the data keeps getting older. */
const STALE_HOURS = 18;
function isStale(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const ms = Date.parse(iso);
  return !isNaN(ms) && Date.now() - ms >= STALE_HOURS * 3600_000;
}

const blank = (v: unknown) => v === null || v === undefined || v === '' || Number.isNaN(Number(v));
const num = (v: unknown, d = 2): string => (blank(v) ? '—' : Number(v).toFixed(d));
const int = (v: unknown): string => (blank(v) ? '—' : String(Math.round(Number(v))));
const yn = (v: unknown): string => (v ? 'Y' : '');

// ------------------------------------------------------------------- types --

type TfView = { status?: string; cmf?: number; cmf20?: number; rsi?: number; rvol?: number; close?: number };
type Coil = { tag: string; pivot15d: number; dist_pct: number };
type View = {
  px_now?: number;
  _stage?: { stage?: string; ext200_pct?: number; trap6?: boolean };
  _coil?: Coil;
  _levels?: Record<string, number>;
} & Partial<Record<Tf, TfView>>;

/** One row of any engine pack (conviction, near_pivot, spring, ez, UIPT picks/rejected). */
interface PackRow {
  sym: string; no?: number;
  score?: number; stage?: string; gloss?: string; horizon?: string; via?: string; action?: string;
  entry_breakout?: number; entry_pullback?: number; stop?: number; stop_tight?: number;
  tp1?: number; tp2?: number; rr_breakout?: number; rr_to_tp1?: number;
  risk_score?: number; ez_stage?: string; default_stage?: string;
  can_enter_now?: boolean; verdict_head?: string; verdict_why?: string;
  enter_from?: string; deadline?: string; confirm_at_both?: string; conflict_caution?: string;
  px_now?: number; rs60?: number; ext200_pct?: number; ext200?: number; w1?: string; rsi?: number;
  coil_tag?: string; atr_pct?: number; upside_to_swinghi_pct?: number;
  rvol1h?: number; cmf1h?: number; dist_pct?: number;
  state?: string; hold_text?: string; sector_flow?: string; entry?: number; entry_rule?: string;
  rr1?: number; rr2?: number; wait_for?: string; time_stop_rule?: string; rr_warning?: string;
  phase4_live?: boolean; gates_failed?: string[];
}
interface HorizonPack {
  mode: string; label: string; x: number; risk_pct?: number[]; max_concurrent?: number;
  picks?: PackRow[]; rejected?: PackRow[]; caveats?: string[];
}
interface Clock {
  bars?: Record<string, { label: string; et: string; th: string }>;
  order?: Record<string, { bar_close: { both: string }; order_open: { both: string } }>;
}
interface Packs {
  conviction?: PackRow[]; near_pivot?: PackRow[]; spring?: PackRow[]; ez?: PackRow[];
  stage_gloss?: Record<string, string>; clock?: Clock; uipt_s?: HorizonPack; uipt_m?: HorizonPack;
}
interface Breadth {
  base_tf?: string; n?: number; gc_d_pct?: number; cmf50_pos_pct?: number; cmf20_pos_pct?: number;
  kill_label?: string; kill_count?: number; kill_list?: string[];
}
interface Metric {
  px?: number; chg_pct?: number; gc_d?: boolean; gc_w?: boolean; rsi_d?: number; cmf_d?: number; cmf20_d?: number;
  ipi_d?: string; ipi_w?: string; above_e200d?: boolean;
}
type SectorRow = { sym: string; [k: string]: string | number | boolean | null | undefined };
interface Full {
  universe?: { stocks?: string[]; etfs?: string[] };
  views?: Record<string, View>;
  regime?: { breadth?: Breadth; tripwires?: Record<string, string>; metrics?: Record<string, Metric> };
  sectors?: SectorRow[]; sanity?: string[]; news?: string[];
}

interface TfMeta {
  symbols_fetched: number; symbols_in_csv: number;
  fetched_at_min: string | null; fetched_at_max: string | null;
  fetched_at_distinct: number; bar_asof: string | null; bar_asof_iso: string | null;
  in_screen: boolean; fetched_at_label: string;
}
interface RoundMeta {
  id: number; stamp: string; fingerprint: string; created_at: string;
  asof_et: string; asof_et_iso: string | null; data_age_hours: number | null;
  timeframes: string[]; tf_meta: Record<string, TfMeta>;
  screen_mode: string; partial: boolean; list_name: string | null;
  universe: { all: number; stocks: number; etfs: number; noneq: number };
  kill_pct: number | null; kill_count: number | null; kill_label: string | null;
  breadth_n: number; regime_hint: string; warnings: string[];
}
interface RoundFull extends RoundMeta { digest_md: string; full: Full | null; packs: Packs | null }
interface TfState {
  has_data?: boolean; symbols_count?: number; fetched_at_max?: string | null;
  fetched_at_distinct?: number; duplicate_symbols?: number; rows_total?: number;
}
interface TfStatus { timeframes?: Partial<Record<Tf, TfState>> }
interface Job { status: string; phase?: string; message?: string; stamp?: string }

// ------------------------------------------------------------ stage badges --

type Tone = { color: 'default' | 'accent' | 'success' | 'warning' | 'danger'; variant: 'primary' | 'secondary' | 'tertiary' | 'soft' };
const STAGE_TONE: Record<string, Tone> = {
  TRIGGER: { color: 'success', variant: 'primary' },
  'TRIGGER-S': { color: 'success', variant: 'primary' },
  SETUP: { color: 'success', variant: 'soft' },
  'SETUP-S': { color: 'success', variant: 'soft' },
  'SETUP(loose)': { color: 'success', variant: 'tertiary' },
  'MACRO-WATCH': { color: 'accent', variant: 'soft' },
  'WATCH(loose)': { color: 'accent', variant: 'tertiary' },
  'WATCH-S': { color: 'accent', variant: 'tertiary' },
  REVERSAL: { color: 'warning', variant: 'tertiary' },
  FAIL: { color: 'default', variant: 'soft' },
  'FAIL-S': { color: 'default', variant: 'soft' },
  KILL: { color: 'danger', variant: 'soft' },
  'KILL-S': { color: 'danger', variant: 'soft' },
  'NO-DATA': { color: 'default', variant: 'tertiary' },
};
const DEFAULT_TONE: Tone = { color: 'default', variant: 'soft' };

// ---------------------------------------------------------------- verdict --
// A mechanical verdict from the round data: enter / watch / rotten. Not a guess:
// only the stage, the weekly money status and whether a full price plan
// (entry/SL/TP) exists decide it.
type Verdict = { icon: string; label: RKey; tone: Tone; order: number };

const V_BUY: Verdict = { icon: '🔥', label: 'vBuy', order: 0, tone: { color: 'warning', variant: 'primary' } };
const V_READY: Verdict = { icon: '🔥', label: 'vReady', order: 1, tone: { color: 'warning', variant: 'soft' } };
const V_ACCUM: Verdict = { icon: '🔥', label: 'vAccum', order: 2, tone: { color: 'accent', variant: 'soft' } };
const V_WATCH: Verdict = { icon: '👀', label: 'vWatch', order: 3, tone: { color: 'accent', variant: 'tertiary' } };
const V_CUT: Verdict = { icon: '😭', label: 'vCut', order: 4, tone: { color: 'danger', variant: 'soft' } };
const V_NONE: Verdict = { icon: '·', label: 'vNone', order: 5, tone: { color: 'default', variant: 'tertiary' } };

function verdictOf(stage?: string, w1Status?: string, hasPlan = false): Verdict {
  const s = String(stage || '');
  if (!s || s === 'NO-DATA') return V_NONE;
  if (s.startsWith('KILL') || s.startsWith('FAIL') || w1Status === 'Dist') return V_CUT;
  if (s === 'TRIGGER' || s === 'TRIGGER-S') return hasPlan ? V_BUY : V_READY;
  if (s === 'SETUP' || s === 'SETUP-S') return hasPlan ? V_READY : V_WATCH;
  return V_WATCH;
}

function VerdictTag({ v }: { v: Verdict }) {
  const t = useT(radarSummary);
  return (
    <Chip size="sm" color={v.tone.color} variant={v.tone.variant} className="whitespace-nowrap font-semibold">
      <span>{v.icon}</span>
      <Chip.Label>{t(v.label)}</Chip.Label>
    </Chip>
  );
}

type HorizonKind = 'short' | 'mid' | 'long';
/** Holding horizon from the formula's (Thai) horizon text — used for the short/mid/long filter. */
function horizonKind(h?: string): HorizonKind {
  const s = String(h || '');
  if (s.includes('ยาว') || /\d+–?\d*M/.test(s) && s.includes('12')) return 'long';
  if (s.trimStart().startsWith('สั้น')) return 'short';
  return 'mid';
}
const KIND_LABEL: Record<HorizonKind, RKey> = { short: 'kindShort', mid: 'kindMid', long: 'kindLong' };
const KIND_CLASS: Record<HorizonKind, string> = {
  short: 'bg-danger-soft text-danger',
  mid: 'bg-success-soft text-success',
  long: 'bg-accent-soft text-accent-soft-foreground',
};

function StageBadge({ stage, gloss }: { stage?: string; gloss?: string }) {
  if (!stage) return <span className="text-muted">—</span>;
  const tone = STAGE_TONE[stage] ?? DEFAULT_TONE;
  const chip = (
    <Chip size="sm" color={tone.color} variant={tone.variant} className="whitespace-nowrap font-mono font-semibold">{stage}</Chip>
  );
  if (!gloss) return chip;
  return (
    <Tooltip delay={300}>
      <Tooltip.Trigger>{chip}</Tooltip.Trigger>
      <Tooltip.Content className="max-w-xs text-xs">{gloss}</Tooltip.Content>
    </Tooltip>
  );
}

// ------------------------------------------------------------------ table --

type Col<T> = { key: string; label: string; render?: (row: T) => ReactNode; right?: boolean; hint?: string };

function DataTable<T extends object>({
  label, cols, rows, empty, max, maxH,
}: { label: string; cols: Col<T>[]; rows: T[]; empty?: string; max?: number; maxH?: string }) {
  const t = useT(radarSummary);
  const lang = useLang();
  const shown = max ? rows.slice(0, max) : rows;
  if (!rows.length) {
    return (
      <p className="flex items-center gap-2 py-2 text-sm italic text-muted">
        <Inbox className="size-4 shrink-0" />{empty ?? t('noData')}
      </p>
    );
  }
  return (
    <div>
      {/* Scrolls both ways (many columns, many rows) with the header kept in view. */}
      <Table variant="secondary">
        <Table.ScrollContainer className={maxH ? `${maxH} overflow-y-auto` : ''}>
          <Table.Content aria-label={label} className="min-w-full text-xs">
            <Table.Header className={maxH ? 'sticky top-0 z-10 bg-surface' : ''}>
              {cols.map((c, i) => {
                // The Thai gloss under each English heading says what the column is for.
                const gloss = c.hint ?? (c.label ? termGloss(c.label, lang) : '');
                return (
                  <Table.Column key={c.key} id={c.key} isRowHeader={i === 0} aria-label={c.label || t('colActions')}
                    className={`align-top ${c.right ? 'text-right' : 'text-left'}`}>
                    <div className="whitespace-nowrap">{c.label}</div>
                    {gloss && (
                      <div className={`max-w-[15rem] whitespace-normal text-[10px] font-normal leading-tight text-muted ${c.right ? 'ml-auto' : ''}`}>
                        {gloss}
                      </div>
                    )}
                  </Table.Column>
                );
              })}
            </Table.Header>
            <Table.Body>
              {shown.map((r, i) => (
                <Table.Row key={i} id={i}>
                  {cols.map((c) => (
                    <Table.Cell key={c.key}
                      className={`whitespace-nowrap ${c.right ? 'text-right font-mono tabular-nums' : ''}`}>
                      {c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? '—')}
                    </Table.Cell>
                  ))}
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Content>
        </Table.ScrollContainer>
      </Table>
      {max && rows.length > max && (
        <p className="pt-2 text-xs text-muted">{t('showingRows', { max, n: rows.length })}</p>
      )}
    </div>
  );
}

function Section({ title, subtitle, children, defaultOpen = true }: {
  title: string; subtitle?: string; children: ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card className="overflow-hidden rounded-2xl p-0">
      <Disclosure isExpanded={open} onExpandedChange={setOpen}>
        <Disclosure.Heading>
          <Disclosure.Trigger className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-surface-secondary">
            <div className="min-w-0">
              <h3 className="text-sm font-bold">{title}</h3>
              {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
            </div>
            <Disclosure.Indicator />
          </Disclosure.Trigger>
        </Disclosure.Heading>
        <Disclosure.Content>
          <div className="px-5 pb-5">{children}</div>
        </Disclosure.Content>
      </Disclosure>
    </Card>
  );
}

/** The three answers (enter now? / from when / latest) the engine attaches to a row. */
function Answer({ r, fallback, extra }: { r: PackRow; fallback?: string; extra?: ReactNode }) {
  const t = useT(radarSummary);
  return (
    <span className="inline-block max-w-[30rem] whitespace-normal leading-relaxed">
      <b className={r.can_enter_now ? 'text-success' : 'text-foreground'}>
        {r.can_enter_now ? '🔥 ' : '⏳ '}{r.verdict_head || fallback || '—'}
      </b>
      {extra ?? (r.verdict_why && <span className="block text-muted">{r.verdict_why}</span>)}
      {r.enter_from && (
        <span className="mt-0.5 block text-success">{t('enterFrom')} <b>{r.enter_from}</b></span>
      )}
      {r.deadline && <span className="block text-muted">{t('deadline')} {r.deadline}</span>}
      {r.conflict_caution && <span className="mt-0.5 block text-warning">{r.conflict_caution}</span>}
    </span>
  );
}

// ================================================================== page ====

export default function RadarView() {
  const { t, time, ago: since } = useFmt();
  const tc = useT(common);
  const confirm = useConfirm();
  const [zone, setZone] = useState<Zone>('TH');
  const [tfStatus, setTfStatus] = useState<TfStatus | null>(null);
  const [picked, setPicked] = useState<Tf[]>([]);
  const [touchedPick, setTouchedPick] = useState(false);
  const [newRecord, setNewRecord] = useState(false);
  const [perPage, setPerPage] = useState(10);
  const [page, setPage] = useState(1);
  const [job, setJob] = useState<Job>({ status: 'idle' });
  const [rounds, setRounds] = useState<RoundMeta[]>([]);
  const pageCount = Math.max(1, Math.ceil(rounds.length / perPage));
  const curPage = Math.min(page, pageCount);      // rounds deleted until the page vanished = fall back to the last page
  const pagedRounds = rounds.slice((curPage - 1) * perPage, curPage * perPage);
  const [round, setRound] = useState<RoundFull | null>(null);
  const [loadingRound, setLoadingRound] = useState(false);
  const [err, setErr] = useState('');

  // ---- data loading -------------------------------------------------------
  const loadTfStatus = useCallback(async () => {
    const r = await axios.get<TfStatus>(`${API_BASE}/api/radar_round/tf_status`);
    setTfStatus(r.data);
    return r.data;
  }, []);

  const loadRounds = useCallback(async () => {
    const r = await axios.get<{ rounds?: RoundMeta[] }>(`${API_BASE}/api/radar_round/list?limit=50`);
    setRounds(r.data.rounds || []);
    return r.data.rounds as RoundMeta[];
  }, []);

  // Rounds are ~0.5MB, so a slow one can land after a later click. Only the
  // newest request is allowed to write state, or the table highlights B while
  // the tables below show A.
  const openSeq = useRef(0);
  const openRound = useCallback(async (stamp: string) => {
    const seq = ++openSeq.current;
    setLoadingRound(true);
    setErr('');
    try {
      const r = await axios.get<RoundFull>(`${API_BASE}/api/radar_round/${stamp}`);
      if (seq === openSeq.current) setRound(r.data);
    } catch (e) {
      if (seq === openSeq.current) setErr(errorDetail(e));
    } finally {
      if (seq === openSeq.current) setLoadingRound(false);
    }
  }, []);

  useEffect(() => {
    // Default zone follows the app-wide timezone setting: an American offset
    // means the user reads ET, anything else gets local (GMT+7) time.
    axios.get(`${API_BASE}/api/settings/timezone`)
      .then((r) => setZone(Number(r.data?.offset_minutes) <= -240 ? 'ET' : 'TH'))
      .catch(() => {});
    axios.get<TfStatus>(`${API_BASE}/api/radar_round/tf_status`)
      .then((r) => {
        setTfStatus(r.data);
        // Pre-tick every timeframe that actually holds data.
        setPicked(TFS.filter((tf) => r.data?.timeframes?.[tf]?.has_data));
      })
      .catch((e) => setErr(errorDetail(e)));
    axios.get<{ rounds?: RoundMeta[] }>(`${API_BASE}/api/radar_round/list?limit=50`)
      .then((r) => {
        const rs = r.data.rounds || [];
        setRounds(rs);
        if (rs.length) void openRound(rs[0].stamp);
      })
      .catch((e) => setErr(errorDetail(e)));
    axios.get<Job>(`${API_BASE}/api/radar_round/status`).then((r) => setJob(r.data)).catch(() => {});
  }, [openRound]);

  // ---- run + poll ---------------------------------------------------------
  const running = job?.status === 'running';

  useEffect(() => {
    if (!running) return;
    const id = setInterval(async () => {
      try {
        const r = await axios.get<Job>(`${API_BASE}/api/radar_round/status`);
        setJob(r.data);
        if (r.data.status !== 'running') {
          clearInterval(id);
          await loadTfStatus();
          await loadRounds();
          if (r.data.stamp) void openRound(r.data.stamp);
        }
      } catch { /* keep polling; a blip shouldn't kill the poller */ }
    }, 2000);
    return () => clearInterval(id);
  }, [running, loadRounds, loadTfStatus, openRound]);

  const runRound = async () => {
    setErr('');
    try {
      const r = await axios.post<Job>(`${API_BASE}/api/radar_round/run`,
        { timeframes: picked, new_record: newRecord });
      setJob(r.data);
    } catch (e) {
      setErr(errorDetail(e));
      // 409 = someone else's round is already running (another tab, or this
      // page reloaded mid-round). Adopt its status so the poller picks it up
      // instead of leaving the page stuck with a dead button.
      if ((e as { response?: { status?: number } }).response?.status === 409) {
        try {
          const s = await axios.get<Job>(`${API_BASE}/api/radar_round/status`);
          setJob(s.data);
        } catch { /* the error message above already explains the state */ }
      }
    }
  };

  const deleteRound = async (stamp: string) => {
    if (!(await confirm({ title: t('deleteTitle', { stamp }), body: t('deleteBody'), confirmLabel: tc('delete') }))) return;
    setErr('');
    try {
      await axios.delete(`${API_BASE}/api/radar_round/${stamp}`);
    } catch (e) {
      setErr(errorDetail(e));
      return;
    }
    notify.success(t('deleted', { stamp }));
    const wasOpen = round?.stamp === stamp;
    if (wasOpen) setRound(null);
    const rs = await loadRounds();
    if (wasOpen && rs?.length) void openRound(rs[0].stamp);
  };

  const downloadDigest = () => {
    if (!round) return;
    const url = URL.createObjectURL(new Blob([round.digest_md], { type: 'text/markdown' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${round.stamp}_digest.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const togglePick = (tf: Tf) => {
    setTouchedPick(true);
    setPicked((p) => (p.includes(tf) ? p.filter((x) => x !== tf) : [...p, tf]));
  };

  const zoneLabel = t(ZONE_LABEL[zone]);
  const phaseText = job.phase === 'building' ? t('phaseBuilding')
    : job.phase === 'screening' ? t('phaseScreening') : t('phaseSaving');
  // Compact page list: always the first/last page and the pages around the current one.
  const pageNums = Array.from({ length: pageCount }, (_, i) => i + 1)
    .filter((n) => n === 1 || n === pageCount || Math.abs(n - curPage) <= 1);

  return (
    <div className="space-y-6">
      {/* ---------------- run panel ---------------- */}
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row flex-wrap items-center gap-3 border-b border-separator pb-4">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-indigo-500/15 text-indigo-600 dark:text-indigo-400">
            <Radar className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('subtitle')}</Card.Description>
          </div>
          <ZoneToggle zone={zone} onChange={setZone} />
        </Card.Header>

        <Card.Content className="space-y-5">
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">{t('step1')}</h3>
              <Button size="sm" variant="ghost" onPress={() => { loadTfStatus().catch((e) => setErr(errorDetail(e))); }}>
                <RefreshCw className="size-3.5" />{tc('refresh')}
              </Button>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {TFS.map((tf) => {
                const s = tfStatus?.timeframes?.[tf];
                const has = !!s?.has_data;
                const on = picked.includes(tf);
                return (
                  <div key={tf} className={`rounded-xl border p-3 transition-colors ${
                    !has ? 'border-separator bg-surface-secondary opacity-60'
                      : on ? 'border-accent bg-accent-soft' : 'border-separator bg-surface hover:bg-surface-secondary'}`}>
                    <Checkbox isDisabled={!has} isSelected={on} onChange={() => togglePick(tf)}>
                      <Checkbox.Content>
                        <Checkbox.Control>
                          <Checkbox.Indicator />
                        </Checkbox.Control>
                        <span className="font-mono font-bold">{tf.toUpperCase()}</span>
                        <span className="text-xs text-muted">
                          {has ? t('tfSymbols', { n: s?.symbols_count ?? 0 }) : t('noData')}
                        </span>
                      </Checkbox.Content>
                    </Checkbox>
                    {has && s && (
                      <div className="mt-2 text-[11px] leading-relaxed text-muted">
                        <div className="flex items-start gap-1">
                          <Clock className="mt-0.5 size-3 shrink-0" />
                          <span>
                            {t('savedToDb')} <b className="text-foreground">{time(s.fetched_at_max, zone)}</b> {zoneLabel}
                            <br />
                            <span className={isStale(s.fetched_at_max) ? 'font-semibold text-warning' : ''}>
                              {since(s.fetched_at_max)}
                              {isStale(s.fetched_at_max) && t('staleRefetch')}
                            </span>
                          </span>
                        </div>
                        {(s.fetched_at_distinct ?? 0) > 1 && (
                          <div className="mt-1 text-warning">{t('multiFetch', { n: s.fetched_at_distinct ?? 0 })}</div>
                        )}
                        {(s.duplicate_symbols ?? 0) > 0 && (
                          <div className="mt-1 text-warning">
                            {t('duplicates', { n: s.duplicate_symbols ?? 0, rows: s.rows_total ?? 0, count: s.symbols_count ?? 0 })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted">{t('savedNote')}</p>
          </div>

          {touchedPick && picked.length > 0 && picked.length < TFS.length && (
            <Alert status="warning">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description className="text-xs">
                  {t('partialWarn')}{!picked.includes('1w') && t('partialNo1w')}
                </Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-separator pt-4">
            <div className="min-h-5 text-xs text-muted">
              {running && (
                <span className="flex items-center gap-2 text-accent">
                  <Spinner size="sm" color="current" />
                  {phaseText} — {job.message}
                </span>
              )}
              {!running && job?.status === 'done' && (
                <span className="flex items-center gap-1.5 text-success">
                  <Check className="size-3.5" /> {job.message} ({job.stamp})
                </span>
              )}
              {!running && job?.status === 'error' && (
                <span className="text-danger">{t('errorPrefix', { message: job.message ?? '' })}</span>
              )}
            </div>
            <Checkbox isSelected={newRecord} onChange={setNewRecord} className="mr-auto max-w-xl">
              <Checkbox.Content>
                <Checkbox.Control>
                  <Checkbox.Indicator />
                </Checkbox.Control>
                <span className="text-xs">{t('newRecord')}</span>
              </Checkbox.Content>
              <Description className="text-[11px]">{t('newRecordHint')}</Description>
            </Checkbox>
            <Button size="lg" onPress={runRound} isPending={running} isDisabled={running || picked.length === 0}>
              {running ? null : <Play className="size-5" />}
              {running ? t('running') : t('run')}
            </Button>
          </div>

          {err && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{err}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
        </Card.Content>
      </Card>

      {/* ---------------- rounds list ---------------- */}
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-bold">
            {t('step2')}{' '}
            <span className="font-normal text-muted">{t('roundsKept', { n: rounds.length })}</span>
          </h3>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted">{t('perPage')}</span>
            <ToggleButtonGroup size="sm" aria-label={t('perPage')} selectionMode="single" disallowEmptySelection
              selectedKeys={[String(perPage)]}
              onSelectionChange={(keys) => { const next = [...keys][0]; if (next) { setPerPage(Number(next)); setPage(1); } }}>
              {[10, 25, 50].map((n, i) => (
                <ToggleButton key={n} id={String(n)} className="min-w-10 font-mono">
                  {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                  {n}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </div>
        </Card.Header>
        <Card.Content className="space-y-3">
          <DataTable<RoundMeta>
            label={t('roundsTable')}
            empty={t('roundsEmpty')}
            rows={pagedRounds}
            cols={[
              {
                key: 'stamp', label: t('colStamp'),
                render: (r) => (
                  <Button size="sm" variant={round?.stamp === r.stamp ? 'secondary' : 'ghost'}
                    aria-label={t('openRound', { stamp: r.stamp })} onPress={() => openRound(r.stamp)}
                    className={`font-mono text-xs font-semibold ${round?.stamp === r.stamp ? 'text-accent' : ''}`}>
                    {r.stamp}
                  </Button>
                ),
              },
              { key: 'asof', label: t('colAsof', { zone: zoneLabel }),
                render: (r) => (
                  <span>
                    {time(r.asof_et_iso || r.asof_et, zone)}{' '}
                    {since(r.asof_et_iso) && (
                      <span className={isStale(r.asof_et_iso) ? 'font-semibold text-warning' : 'text-muted'}>
                        ({since(r.asof_et_iso)})
                      </span>
                    )}
                  </span>
                ) },
              { key: 'tfs', label: 'timeframes', render: (r) => <TfBadges r={r} /> },
              { key: 'universe', label: 'universe', right: true, render: (r) => r.universe?.all ?? '—' },
              { key: 'kill', label: 'kill%', right: true,
                render: (r) => (
                  <span className={Number(r.kill_pct) >= 50 ? 'font-semibold text-danger' : ''}>
                    {num(r.kill_pct, 1)}%
                  </span>
                ) },
              { key: 'regime', label: 'regime', render: (r) => <RegimeBadge hint={r.regime_hint} /> },
              { key: 'created', label: t('colCreated', { zone: zoneLabel }), render: (r) => time(r.created_at, zone) },
              { key: 'del', label: '', right: true,
                render: (r) => (
                  <Tooltip delay={300}>
                    <Button isIconOnly size="sm" variant="ghost" aria-label={t('deleteRound')}
                      className="text-muted hover:text-danger" onPress={() => deleteRound(r.stamp)}>
                      <Trash2 className="size-3.5" />
                    </Button>
                    <Tooltip.Content>{t('deleteRound')}</Tooltip.Content>
                  </Tooltip>
                ) },
            ]}
          />
          {pageCount > 1 && (
            <Pagination size="sm" className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <Pagination.Summary className="text-xs text-muted">
                {t('pageSummary', {
                  from: (curPage - 1) * perPage + 1, to: Math.min(curPage * perPage, rounds.length), total: rounds.length,
                })}
              </Pagination.Summary>
              <Pagination.Content aria-label={t('pages')}>
                <Pagination.Item>
                  <Pagination.Previous isDisabled={curPage === 1} onPress={() => setPage(1)} aria-label={t('first')}>
                    «
                  </Pagination.Previous>
                </Pagination.Item>
                <Pagination.Item>
                  <Pagination.Previous isDisabled={curPage === 1} onPress={() => setPage(curPage - 1)}>
                    <Pagination.PreviousIcon />
                    <span className="hidden sm:inline">{t('prev')}</span>
                  </Pagination.Previous>
                </Pagination.Item>
                {pageNums.map((n, i, arr) => (
                  <PageLink key={n} n={n} active={n === curPage} gap={i > 0 && arr[i - 1] !== n - 1} onPress={() => setPage(n)} />
                ))}
                <Pagination.Item>
                  <Pagination.Next isDisabled={curPage === pageCount} onPress={() => setPage(curPage + 1)}>
                    <span className="hidden sm:inline">{t('next')}</span>
                    <Pagination.NextIcon />
                  </Pagination.Next>
                </Pagination.Item>
                <Pagination.Item>
                  <Pagination.Next isDisabled={curPage === pageCount} onPress={() => setPage(pageCount)} aria-label={t('last')}>
                    »
                  </Pagination.Next>
                </Pagination.Item>
              </Pagination.Content>
            </Pagination>
          )}
        </Card.Content>
      </Card>

      {/* ---------------- selected round ---------------- */}
      {loadingRound && (
        <Card className="space-y-3 rounded-2xl" aria-busy>
          <div className="flex items-center gap-2 text-sm text-muted">
            <Spinner size="sm" /> {t('loadingRound')}
          </div>
          <Skeleton className="h-6 w-1/3 rounded-lg" />
          <Skeleton className="h-4 w-2/3 rounded-lg" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </Card>
      )}
      {round && !loadingRound && (
        <RoundDetail round={round} zone={zone} onDownload={downloadDigest} />
      )}
    </div>
  );
}

// --------------------------------------------------------------- fragments --

function PageLink({ n, active, gap, onPress }: { n: number; active: boolean; gap: boolean; onPress: () => void }) {
  return (
    <>
      {gap && (
        <Pagination.Item>
          <Pagination.Ellipsis />
        </Pagination.Item>
      )}
      <Pagination.Item>
        <Pagination.Link isActive={active} onPress={onPress} className="font-mono">{n}</Pagination.Link>
      </Pagination.Item>
    </>
  );
}

function ZoneToggle({ zone, onChange }: { zone: Zone; onChange: (z: Zone) => void }) {
  const t = useT(radarSummary);
  return (
    <ToggleButtonGroup size="sm" aria-label={t('zone')} selectionMode="single" disallowEmptySelection
      selectedKeys={[zone]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) onChange(next as Zone); }}>
      {(['ET', 'TH'] as Zone[]).map((z, i) => (
        <Tooltip key={z} delay={300}>
          <ToggleButton id={z} className="min-w-14 font-semibold">
            {i > 0 ? <ToggleButtonGroup.Separator /> : null}
            {z === 'ET' ? 'ET' : 'GMT+7'}
          </ToggleButton>
          <Tooltip.Content>{t(ZONE_LABEL[z])}</Tooltip.Content>
        </Tooltip>
      ))}
    </ToggleButtonGroup>
  );
}

function TfBadges({ r }: { r: RoundMeta }) {
  const label = (r.timeframes || []).map((tf) => tf.toUpperCase()).join('+');
  return r.partial ? (
    <Chip size="sm" color="warning" variant="soft" className="whitespace-nowrap font-semibold">
      <AlertTriangle className="size-3" />
      <Chip.Label>PARTIAL {label}</Chip.Label>
    </Chip>
  ) : (
    <Chip size="sm" color="success" variant="soft" className="whitespace-nowrap font-semibold">FULL {label}</Chip>
  );
}

function RegimeBadge({ hint }: { hint?: string }) {
  if (!hint) return <span className="text-muted">—</span>;
  const off = hint.startsWith('RISK-OFF');
  const trans = hint.startsWith('TRANSITION') || hint.startsWith('SELECTIVE');
  return (
    <Chip size="sm" variant="soft" color={off ? 'danger' : trans ? 'warning' : 'success'} className="whitespace-nowrap font-semibold">
      {off ? '🔴' : trans ? '🟠' : '🟢'} {hint}
    </Chip>
  );
}

// ------------------------------------------------------------ round detail --

type PlayFilter = 'all' | 'fire' | HorizonKind;
type Src = { key: 'srcScore' | 'srcSpring'; n: number | string } | { key: 'srcNear' } | { text: string };
type Play = PackRow & {
  src: Src[];
  horizonKey?: RKey; glossKey?: RKey; entryLabel?: RKey;
  risk?: number; hasPlan?: boolean; kind?: HorizonKind; verdict?: Verdict;
};
type Warning = { text: string } | { stale: true };

function RoundDetail({ round, zone, onDownload }: {
  round: RoundFull; zone: Zone; onDownload: () => void;
}) {
  const { t, time, ago: since } = useFmt();
  const full: Full = round.full || {};
  const packs: Packs = round.packs || {};
  const views = full.views || {};
  const zoneLabel = t(ZONE_LABEL[zone]);

  // Derive from `round` (a stable prop) rather than from the `|| {}` fallbacks
  // above — those build a fresh object on every render and would defeat useMemo.
  const names: string[] = useMemo(() => {
    const u = round.full?.universe || {};
    return [...(u.stocks || []), ...(u.etfs || [])];
  }, [round]);

  const [stageFilter, setStageFilter] = useState('actionable');
  const [q, setQ] = useState('');

  // Names with a full price plan (entry/SL/TP): separates "really enterable" from "passed a gate".
  const planned = useMemo(() => {
    const p = round.packs || {};
    return new Set<string>([...(p.conviction || []), ...(p.near_pivot || [])].map((r) => r.sym));
  }, [round]);

  const stageRows = useMemo(() => {
    const vs = round.full?.views || {};
    const gloss = round.packs?.stage_gloss || {};
    const rows = names.map((s) => {
      const v: View = vs[s] || {};
      const st = v._stage || {};
      const w1 = v['1w'] || {};
      return {
        sym: s, stage: st.stage, gloss: st.stage ? gloss[st.stage] : undefined,
        verdict: verdictOf(st.stage, w1.status, planned.has(s)),
        px: v.px_now, d1: v['1d'] || {}, w1, h1: v['1h'] || {},
        h4: v['4h'] || {}, ext: st.ext200_pct, trap6: st.trap6, coil: v._coil,
      };
    });
    const dead = ['KILL', 'KILL-S', 'FAIL', 'FAIL-S', 'NO-DATA'];
    return rows
      .filter((r) => {
        if (q && !r.sym.toLowerCase().includes(q.toLowerCase())) return false;
        if (stageFilter === 'all') return true;
        if (stageFilter === 'actionable') return !dead.includes(r.stage ?? '');
        if (stageFilter === 'kill') return String(r.stage || '').startsWith('KILL');
        if (stageFilter === 'cut') return r.verdict === V_CUT;
        return r.stage === stageFilter;
      })
      .sort((a, b) => a.verdict.order - b.verdict.order
        || String(a.stage).localeCompare(String(b.stage)) || a.sym.localeCompare(b.sym));
  }, [names, round, q, stageFilter, planned]);

  // ---- "what to play": every screen merged into one ranking with horizon and price plan ----
  const [playFilter, setPlayFilter] = useState<PlayFilter>('all');
  const plays = useMemo(() => {
    const p = round.packs || {};
    const vs = round.full?.views || {};
    const byS = new Map<string, Play>();
    const put = (sym: string, row: Omit<Play, 'sym' | 'src'>, src: Src) => {
      const cur = byS.get(sym);
      if (cur) { cur.src.push(src); return; }        // the first screen wins (ordered finest first)
      byS.set(sym, { ...row, sym, src: [src] });
    };

    // The three answers (enter now? / from when / latest) come from the backend as a set.
    const ans = (r: PackRow) => ({
      can_enter_now: r.can_enter_now, verdict_head: r.verdict_head,
      verdict_why: r.verdict_why, enter_from: r.enter_from, deadline: r.deadline,
      confirm_at_both: r.confirm_at_both,
    });

    // 1) conviction: full plan + score + horizon (the finest)
    for (const r of (p.conviction || [])) {
      put(r.sym, {
        score: r.score, stage: r.stage, gloss: r.gloss, horizon: r.horizon,
        entry: r.entry_breakout, entryLabel: 'entryBreak', stop: r.stop_tight,
        tp1: r.tp1, tp2: r.tp2, rr1: r.rr_breakout, entry_pullback: r.entry_pullback,
        ...ans(r),
      }, { key: 'srcScore', n: r.score ?? '' });
    }
    // 2) near the line ≤2.5%: short trade, buy the breakout
    for (const r of (p.near_pivot || [])) {
      put(r.sym, {
        score: undefined, stage: r.stage, gloss: r.gloss,
        horizonKey: 'nearHorizon', kind: 'short',
        entry: r.entry_breakout, entryLabel: 'entryBreak', stop: r.stop,
        tp1: r.tp1, tp2: r.tp2, rr1: r.rr_to_tp1, ...ans(r),
      }, { key: 'srcNear' });
    }
    // 3) springs: cheap and about to bounce, held long
    for (const r of (p.spring || [])) {
      put(r.sym, {
        stage: 'SPRING', glossKey: 'springGloss',
        horizonKey: 'springHorizon', kind: 'long', risk: r.risk_score,
        entry: r.entry_pullback, entryLabel: 'entryPull', stop: r.stop, tp1: r.tp1, ...ans(r),
      }, { key: 'srcSpring', n: r.risk_score ?? '' });
    }
    // 4) -ez: names the strict screen cut, kept to watch
    for (const r of (p.ez || [])) {
      put(r.sym, {
        stage: r.ez_stage, gloss: r.gloss, horizon: r.horizon, action: r.action, ...ans(r),
      }, { text: '-ez' });
    }

    return [...byS.values()].map((r) => {
      const w1 = (vs[r.sym] || {})['1w'] || {};
      const hasPlan = r.entry != null && r.stop != null && r.tp1 != null;
      return { ...r, hasPlan, kind: r.kind ?? horizonKind(r.horizon),
               verdict: r.stage === 'SPRING' && w1.status !== 'Dist'
                 ? V_ACCUM
                 : verdictOf(r.stage === 'SPRING' ? 'MACRO-WATCH' : r.stage, w1.status, hasPlan) };
    }).sort((a, b) => a.verdict.order - b.verdict.order
      || (b.score || 0) - (a.score || 0)
      || (a.risk ?? 99) - (b.risk ?? 99)
      || a.sym.localeCompare(b.sym));
  }, [round]);

  const playsShown = plays.filter((r) => playFilter === 'all'
    || (playFilter === 'fire' ? r.verdict.icon === '🔥' : r.kind === playFilter));

  // ❌ Do-not-touch names of the short queue: neat near the line but cut dead — where people slip in.
  const forbidden = useMemo(() => {
    const vs = round.full?.views || {};
    const gloss = round.packs?.stage_gloss || {};
    return names.map((s) => {
      const v: View = vs[s] || {};
      const st = (v._stage || {}).stage;
      if (!st || !(st.startsWith('KILL') || st.startsWith('FAIL'))) return null;
      const dist = v._coil?.dist_pct;
      if (dist == null || dist < -2.5 || dist > 0.5) return null;   // only the ones that "look enterable"
      const w1 = v['1w'] || {}, d1 = v['1d'] || {};
      const why: RKey = w1.status === 'Dist' ? 'whyW1'
        : d1.status === 'Dist' ? 'whyD1'
        : st.startsWith('FAIL') ? 'whyFail'
        : 'whyKill';
      return { sym: s, stage: st, gloss: gloss[st], dist, pivot: v._coil?.pivot15d, why };
    }).filter((r): r is NonNullable<typeof r> => r !== null)
      .sort((a, b) => b.dist - a.dist);
  }, [names, round]);

  // The stored warnings describe the round at the moment it was computed; this
  // one is about right now, because a reused round never gets recomputed while
  // its data keeps ageing.
  const warnings = useMemo<Warning[]>(() => {
    const w: Warning[] = (round.warnings || []).map((text) => ({ text }));
    if (isStale(round.asof_et_iso) && !(round.warnings || []).some((x) => x.startsWith('ข้อมูลในรอบนี้เก่ากว่า'))) {
      w.unshift({ stale: true });
    }
    return w;
  }, [round]);

  const clock = packs.clock;               // bar-close / order days (ET + Thai)
  const breadth: Breadth = full.regime?.breadth || {};
  const tripwires = Object.entries(full.regime?.tripwires || {});
  const metrics = Object.entries(full.regime?.metrics || {});
  const short = round.screen_mode === 'short';
  const srcText = (s: Src) => ('text' in s ? s.text : s.key === 'srcNear' ? t('srcNear') : t(s.key, { n: s.n }));

  const playFilters: [PlayFilter, RKey][] = [
    ['all', 'fAll'], ['fire', 'fFire'], ['short', 'fShort'], ['mid', 'fMid'], ['long', 'fLong'],
  ];
  const stageFilters: [string, string][] = [
    ['actionable', t('sfActionable')], ['all', t('fAll')], ['cut', t('sfCut')],
    ['TRIGGER', 'TRIGGER'], ['SETUP', 'SETUP'], ['MACRO-WATCH', 'MACRO-WATCH'], ['kill', 'KILL'],
  ];

  return (
    <div className="space-y-4">
      {/* header */}
      <Card className="space-y-3 rounded-2xl border border-accent/30">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-mono text-lg font-bold">{round.stamp}</h2>
              <TfBadges r={round} />
              <Chip size="sm" variant="tertiary" className="font-semibold">
                {t('modeBadge', { mode: String(round.screen_mode).toUpperCase() })}
              </Chip>
              <RegimeBadge hint={round.regime_hint} />
            </div>
            <p className="mt-1 text-xs text-muted">
              {t('asofLine')} <b className="text-foreground">{time(round.asof_et_iso || round.asof_et, zone)}</b> {zoneLabel}
              {' '}
              {since(round.asof_et_iso) && (
                <span className={isStale(round.asof_et_iso) ? 'font-semibold text-warning' : ''}>
                  ({since(round.asof_et_iso)})
                </span>
              )}
              {' · '}{t('computedAt', { time: time(round.created_at, zone) })}
              {' · '}{t('universeLine', { all: round.universe?.all ?? '—', stocks: round.universe?.stocks ?? '—', etfs: round.universe?.etfs ?? '—' })}
              {' · '}fingerprint <span className="font-mono">{round.fingerprint?.slice(0, 8)}</span>
            </p>
          </div>
          <Button size="sm" variant="secondary" onPress={onDownload}>
            <Download className="size-3.5" />{t('downloadDigest')}
          </Button>
        </div>

        {warnings.length > 0 && (
          <Alert status="warning">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Title className="text-xs font-bold">{t('warningsTitle')}</Alert.Title>
              <Alert.Description>
                <ul className="mt-1 space-y-1">
                  {warnings.map((w, i) => (
                    <li key={i} className="text-xs leading-relaxed">
                      • {'text' in w ? w.text : t('staleWarning', {
                        ago: since(round.asof_et_iso), asof: String(round.asof_et).slice(0, 16),
                      })}
                    </li>
                  ))}
                </ul>
              </Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </Card>

      {/* ---------- the round's clock: what to wait for, close times, order days ---------- */}
      {clock?.bars && (
        <Card variant="secondary" className="rounded-2xl">
          <h3 className="text-sm font-bold">{t('clockTitle')}</h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {TFS.filter((tf) => clock.bars?.[tf]).map((tf) => {
              const bar = clock.bars![tf];
              return (
                <div key={tf} className="rounded-lg border border-separator bg-surface px-3 py-2">
                  <p className="text-[11px] text-muted">{bar.label}</p>
                  <p className="mt-0.5 font-mono text-xs font-semibold">{bar.et}</p>
                  <p className="font-mono text-xs text-accent">{bar.th}</p>
                </div>
              );
            })}
          </div>
          {clock.order?.['1d'] && (
            <p className="text-xs leading-relaxed">
              <b>{t('orderWhen')}</b> {t('orderMidA')}{' '}
              <b>{clock.order['1d'].bar_close.both}</b> {t('orderMidB')}{' '}
              <b className="text-success">{clock.order['1d'].order_open.both}</b>
              {clock.order['4h'] && (
                <>{t('orderShortA')} <b>{clock.order['4h'].bar_close.both}</b>{' '}
                  {t('orderShortB')} <b className="text-success">{clock.order['4h'].order_open.both}</b></>
              )}
            </p>
          )}
          <p className="text-[11px] text-muted">{t('clockNote')}</p>
        </Card>
      )}

      {/* ---------- what to play (the answer before the numbers) ---------- */}
      <Card className="rounded-2xl border-2 border-warning/40">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-base font-bold">{t('playsTitle')}</h3>
          <span className="text-xs text-muted">{t('playsCount', { n: plays.length })}</span>
        </div>
        <p className="text-xs text-muted">{t('playsLegend')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <ToggleButtonGroup size="sm" aria-label={t('playFilter')} selectionMode="single" disallowEmptySelection
            selectedKeys={[playFilter]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setPlayFilter(next as PlayFilter); }}
            className="flex-wrap">
            {playFilters.map(([v, label], i) => (
              <ToggleButton key={v} id={v}>
                {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                {t(label)}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <span className="text-xs text-muted">{t('nNames', { n: playsShown.length })}</span>
        </div>
        <DataTable
          label={t('playsTable')}
          maxH="max-h-[36rem]"
          rows={playsShown}
          empty={t('playsEmpty')}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono text-sm">{r.sym}</b> },
            { key: 'verdict', label: t('colWhatToDo'), hint: t('hWhatToDo'), render: (r) => <VerdictTag v={r.verdict} /> },
            { key: 'horizon', label: t('colHold'), hint: t('hHold'),
              render: (r) => (
                <span>
                  <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${KIND_CLASS[r.kind]}`}>{t(KIND_LABEL[r.kind])}</span>
                  <div className="mt-0.5 max-w-[13rem] whitespace-normal text-[10px] text-muted">
                    {r.horizonKey ? t(r.horizonKey) : r.horizon}
                  </div>
                </span>
              ) },
            { key: 'stage', label: 'stage',
              render: (r) => <StageBadge stage={r.stage} gloss={r.glossKey ? t(r.glossKey) : r.gloss} /> },
            { key: 'gloss', label: t('colAnswer'), hint: t('hAnswer'),
              render: (r) => <Answer r={r} fallback={r.action || (r.glossKey ? t(r.glossKey) : r.gloss)} /> },
            { key: 'entry', label: 'entry >', hint: t('hEntry'), right: true,
              render: (r) => (r.entry == null ? <span className="text-muted">—</span>
                : <span><span className="text-[10px] text-muted">{r.entryLabel ? t(r.entryLabel) : ''} </span>{num(r.entry)}</span>) },
            { key: 'stop', label: 'SL', right: true, render: (r) => num(r.stop) },
            { key: 'tp1', label: 'TP1', right: true, render: (r) => num(r.tp1) },
            { key: 'tp2', label: 'TP2', right: true, render: (r) => num(r.tp2) },
            { key: 'rr', label: 'R:R', right: true,
              render: (r) => (r.rr1 == null ? '—'
                : <span className={Number(r.rr1) >= 1.5 ? 'font-semibold text-success' : 'text-muted'}>{num(r.rr1, 2)}</span>) },
            { key: 'src', label: t('colSource'), hint: t('hSource'),
              render: (r) => <span className="text-muted">{r.src.map(srcText).join(' · ')}</span> },
          ]}
        />
      </Card>

      <Section title={t('s1Title')} subtitle={t('s1Sub')}>
        <DataTable
          label={t('s1Table')}
          rows={TFS.filter((tf) => round.tf_meta?.[tf]).map((tf) => ({ tf, ...round.tf_meta[tf] }))}
          cols={[
            { key: 'tf', label: 'TF', render: (r) => <b className="font-mono">{r.tf.toUpperCase()}</b> },
            { key: 'sym', label: 'symbols', right: true, render: (r) => r.symbols_in_csv },
            { key: 'fetch', label: t('colSaved', { zone: zoneLabel }),
              render: (r) => (
                <span>{time(r.fetched_at_max, zone)}{' '}
                  <span className={isStale(r.fetched_at_max) ? 'font-semibold text-warning' : 'text-muted'}>
                    ({since(r.fetched_at_max)})
                  </span>
                </span>
              ) },
            { key: 'in', label: t('colInScreen'),
              render: (r) => (r.in_screen
                ? <Check className="size-3.5 text-success" />
                : <span className="text-xs text-danger">{t('notUsed')}</span>) },
          ]}
        />
      </Section>

      <Section title={t('s2Title')} subtitle={`permission hint: ${round.regime_hint}`}>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted">Tripwires</p>
            <ul className="space-y-1">
              {tripwires.map(([k, v]) => (
                <li key={k} className="flex justify-between gap-3 border-b border-separator py-1 text-xs">
                  <span className="shrink-0 text-muted">{k}</span>
                  <span className={`min-w-0 break-words text-right font-mono ${/BELOW|backwardation/.test(String(v)) ? 'font-semibold text-danger' : ''}`}>{String(v)}</span>
                </li>
              ))}
              {!tripwires.length && <li className="text-xs italic text-muted">{t('noMacro')}</li>}
            </ul>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted">
              {t('breadthTitle', { tf: String(breadth.base_tf || '').toUpperCase(), n: breadth.n ?? '—' })}
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Stat label="Golden Cross" value={`${breadth.gc_d_pct ?? '—'}%`} />
              <Stat label="CMF50 > 0" value={`${breadth.cmf50_pos_pct ?? '—'}%`} />
              <Stat label="CMF20 > 0" value={`${breadth.cmf20_pos_pct ?? '—'}%`} />
              <Stat label={breadth.kill_label || 'kill'}
                value={`${breadth.kill_count ?? '—'}/${breadth.n ?? '—'} (${num(round.kill_pct, 1)}%)`}
                danger={Number(round.kill_pct) >= 50} />
            </div>
            {(breadth.kill_list?.length ?? 0) > 0 && (
              <Disclosure className="mt-2">
                {({ isExpanded }) => (
                  <>
                    <Disclosure.Heading>
                      <Disclosure.Trigger className="flex items-center gap-1 text-xs text-accent">
                        {isExpanded
                          ? t('hideKillList', { label: breadth.kill_label ?? 'kill' })
                          : t('killList', { label: breadth.kill_label ?? 'kill', n: breadth.kill_list?.length ?? 0 })}
                        <Disclosure.Indicator />
                      </Disclosure.Trigger>
                    </Disclosure.Heading>
                    <Disclosure.Content>
                      <p className="mt-1 font-mono text-[11px] leading-relaxed text-muted">{breadth.kill_list?.join(', ')}</p>
                    </Disclosure.Content>
                  </>
                )}
              </Disclosure>
            )}
          </div>
        </div>
        <div className="mt-4">
          <p className="mb-1.5 text-xs font-semibold text-muted">Macro / indices</p>
          <DataTable
            label={t('macroTable')}
            rows={metrics.map(([sym, m]) => ({ sym, ...m }))}
            cols={[
              { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
              { key: 'px', label: 'px', right: true, render: (r) => num(r.px) },
              { key: 'chg', label: 'chg%', right: true,
                render: (r) => <span className={Number(r.chg_pct) < 0 ? 'text-danger' : 'text-success'}>{num(r.chg_pct)}</span> },
              { key: 'gc', label: 'GC d/w', render: (r) => `${yn(r.gc_d) || '·'}/${yn(r.gc_w) || '·'}` },
              { key: 'rsi', label: 'RSI', right: true, render: (r) => int(r.rsi_d) },
              { key: 'cmf', label: 'CMF50/20', right: true, render: (r) => `${num(r.cmf_d, 3)}/${num(r.cmf20_d, 3)}` },
              { key: 'ipi', label: 'IPI d/w', render: (r) => `${r.ipi_d ?? '—'}/${r.ipi_w ?? '—'}` },
              { key: 'e200', label: '>E200d', render: (r) => (r.above_e200d ? 'Y' : 'N') },
            ]}
          />
        </div>
      </Section>

      <Section title={t('s3Title')}>
        <DataTable<SectorRow>
          label={t('sectorsTable')}
          rows={full.sectors || []}
          cols={[
            { key: 'sym', label: 'ETF', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'cmf', label: 'cmf20 1h/4h/1d/1w',
              render: (r) => ['1h', '4h', '1d', '1w']
                .map((tf) => (r[`cmf20_${tf}`] == null ? '—' : Number(r[`cmf20_${tf}`]).toFixed(2)))
                .join(' / ') },
            { key: 'ipi', label: 'IPI d/w', render: (r) => `${r.ipi_d ?? '—'}/${r.ipi_w ?? '—'}` },
            { key: 'rs20', label: 'RS20', right: true,
              render: (r) => <span className={Number(r.rs20) > 0 ? 'font-semibold text-success' : 'text-muted'}>{num(r.rs20, 1)}</span> },
            { key: 'rs60', label: 'RS60', right: true, render: (r) => num(r.rs60, 1) },
            { key: 'gc_d', label: 'GCd', render: (r) => yn(r.gc_d) },
            { key: 'rsi_d', label: 'RSI', right: true, render: (r) => int(r.rsi_d) },
          ]}
        />
      </Section>

      <HorizonSection pack={packs.uipt_s} />
      <HorizonSection pack={packs.uipt_m} />

      <Section title={short ? t('s4TitleShort') : t('s4TitleFull')}
        subtitle={t('s4Sub', { k: breadth.kill_count ?? '—', n: breadth.n ?? '—' })}>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <SearchField aria-label={t('searchSymbol')} value={q} onChange={setQ} className="w-44">
            <SearchField.Group>
              <SearchField.SearchIcon />
              <SearchField.Input placeholder={t('searchSymbol')} className="text-xs" />
              <SearchField.ClearButton />
            </SearchField.Group>
          </SearchField>
          <ToggleButtonGroup size="sm" aria-label={t('stageFilter')} selectionMode="single" disallowEmptySelection
            selectedKeys={[stageFilter]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setStageFilter(String(next)); }}
            className="flex-wrap">
            {stageFilters.map(([v, label], i) => (
              <ToggleButton key={v} id={v}>
                {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                {label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <span className="text-xs text-muted">{t('nNames', { n: stageRows.length })}</span>
        </div>
        <DataTable
          label={t('stageTable')}
          maxH="max-h-[32rem]"
          rows={stageRows}
          empty={t('stageEmpty')}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'verdict', label: t('colWhatToDo'), hint: t('hVerdictShort'), render: (r) => <VerdictTag v={r.verdict} /> },
            { key: 'stage', label: 'stage', render: (r) => <StageBadge stage={r.stage} gloss={r.gloss} /> },
            { key: 'gloss', label: t('colPlain'), render: (r) => <span className="text-muted">{r.gloss || '—'}</span> },
            { key: 'px', label: 'px_now', right: true, render: (r) => num(r.px) },
            { key: 'closed', label: short ? 'close_4h' : 'close_d', right: true,
              render: (r) => num(short ? r.h4.close : r.d1.close) },
            { key: 'w1', label: '1W cmf/IPI', render: (r) => `${num(r.w1.cmf, 3)}/${r.w1.status ?? '—'}` },
            { key: 'd1', label: short ? '4H cmf20/IPI/RSI' : '1D cmf20/IPI/RSI',
              render: (r) => {
                const tv = short ? r.h4 : r.d1;
                return `${num(tv.cmf20, 3)}/${tv.status ?? '—'}/${int(tv.rsi)}`;
              } },
            { key: 'h1', label: '1H cmf20/IPI/rvol',
              render: (r) => `${num(r.h1.cmf20, 3)}/${r.h1.status ?? '—'}/${num(r.h1.rvol, 2)}` },
            { key: 'ext', label: 'ext200%', right: true,
              render: (r) => <span className={Number(r.ext) > 50 ? 'font-semibold text-warning' : ''}>{int(r.ext)}</span> },
            { key: 'trap', label: 'trap6', render: (r) => (r.trap6 ? <span className="font-bold text-danger">Y</span> : '') },
            { key: 'coil', label: 'coil',
              render: (r) => (r.coil
                ? `${r.coil.tag} piv=${r.coil.pivot15d} (${r.coil.dist_pct > 0 ? '+' : ''}${r.coil.dist_pct}%)`
                : '') },
          ]}
        />
      </Section>

      <Section title={t('s5Title')} subtitle={t('s5Sub')}>
        <DataTable
          label={t('nearTable')}
          rows={(packs.near_pivot || []).map((r, i) => ({ ...r, no: i + 1 }))}
          empty={t('nearEmpty')}
          cols={[
            { key: 'no', label: '#', hint: t('hNo') },
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'stage', label: 'stage', render: (r) => <StageBadge stage={r.stage} gloss={r.gloss} /> },
            { key: 'gloss', label: t('colPlain'), render: (r) => r.gloss },
            { key: 'entry', label: 'trigger', hint: t('hTrigger'), right: true, render: (r) => <b>{num(r.entry_breakout)}</b> },
            { key: 'stop', label: 'SL', right: true, render: (r) => num(r.stop) },
            { key: 'tp1', label: 'TP1', right: true, render: (r) => num(r.tp1) },
            { key: 'tp2', label: 'TP2', right: true, render: (r) => num(r.tp2) },
            { key: 'rr', label: 'R:R', right: true, render: (r) => num(r.rr_to_tp1, 2) },
            { key: 'cond', label: t('colAnswer'), hint: t('hAnswerCond'),
              render: (r) => (
                <Answer r={r} extra={(
                  <span className="block text-muted">
                    {t('nearCond', { entry: num(r.entry_breakout), rvol: num(r.rvol1h, 2), cmf: num(r.cmf1h, 3), dist: num(r.dist_pct, 1) })}
                  </span>
                )} />
              ) },
          ]}
        />
        <div className="mt-4">
          <p className="mb-1.5 text-xs font-bold text-danger">{t('forbiddenTitle')}</p>
          <DataTable
            label={t('forbiddenTable')}
            rows={forbidden}
            empty={t('forbiddenEmpty')}
            cols={[
              { key: 'sym', label: 'sym', render: (r) => <b className="font-mono text-danger">❌ {r.sym}</b> },
              { key: 'stage', label: 'stage', render: (r) => <StageBadge stage={r.stage} gloss={r.gloss} /> },
              { key: 'dist', label: t('colDistPivot'), right: true, render: (r) => num(r.dist, 1) },
              { key: 'pivot', label: 'pivot', right: true, render: (r) => num(r.pivot) },
              { key: 'why', label: t('colWhy'), hint: t('hWhy'), render: (r) => <span className="text-danger">{t(r.why)}</span> },
            ]}
          />
        </div>
      </Section>

      <Section title={t('s6Title')} subtitle={t('s6Sub')}>
        <DataTable
          label={t('convTable')}
          rows={packs.conviction || []}
          empty={t('convEmpty')}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'score', label: 'score', right: true, render: (r) => <span className="font-bold text-accent">{num(r.score, 1)}</span> },
            { key: 'via', label: 'via' },
            { key: 'stage', label: 'stage', render: (r) => <StageBadge stage={r.stage} gloss={r.gloss} /> },
            { key: 'horizon', label: t('colHowLong') },
            { key: 'entryq', label: t('colAnswer'), hint: t('hAnswer'), render: (r) => <Answer r={r} /> },
            { key: 'brk', label: t('colBreakoutPlan'),
              render: (r) => t('breakoutPlan', { entry: num(r.entry_breakout), sl: num(r.stop_tight), rr: num(r.rr_breakout, 2) }) },
            { key: 'pb', label: t('colPullbackPlan'),
              render: (r) => t('pullbackPlan', { entry: num(r.entry_pullback), sl: num(r.stop) }) },
            { key: 'tp1', label: 'TP1', right: true, render: (r) => num(r.tp1) },
            { key: 'tp2', label: 'TP2', right: true, render: (r) => num(r.tp2) },
          ]}
        />
      </Section>

      <Section title={t('s7Title')} subtitle={t('s7Sub')}>
        <DataTable
          label={t('ezTable')}
          rows={packs.ez || []}
          empty={t('ezEmpty')}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'flip', label: 'default → ez',
              render: (r) => <span className="inline-flex items-center gap-1">{r.default_stage} → <StageBadge stage={r.ez_stage} gloss={r.gloss} /></span> },
            { key: 'px', label: 'px', right: true, render: (r) => num(r.px_now) },
            { key: 'rs60', label: 'RS60', right: true, render: (r) => num(r.rs60, 1) },
            { key: 'ext', label: 'ext%', right: true, render: (r) => int(r.ext200_pct) },
            { key: 'horizon', label: t('colHowLong') },
            { key: 'entryq', label: t('colAnswer'), hint: t('hAnswer'), render: (r) => <Answer r={r} /> },
            { key: 'action', label: t('colAction') },
          ]}
        />
      </Section>

      <Section title={t('s8Title')} subtitle={t('s8Sub')}>
        <DataTable
          label={t('springTable')}
          rows={packs.spring || []}
          empty={t('springEmpty')}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'risk', label: 'risk↓', right: true, render: (r) => <span className="font-bold">{num(r.risk_score, 1)}</span> },
            { key: 'ext', label: 'ext%', right: true, render: (r) => int(r.ext200) },
            { key: 'rs60', label: 'RS60', right: true, render: (r) => num(r.rs60, 1) },
            { key: 'w1', label: '1W' },
            { key: 'rsi', label: 'RSI', right: true, render: (r) => int(r.rsi) },
            { key: 'coil', label: 'coil', render: (r) => r.coil_tag || (r.atr_pct ? `ATR${r.atr_pct}%` : '—') },
            { key: 'upside', label: 'upside%', right: true, render: (r) => int(r.upside_to_swinghi_pct) },
            { key: 'entryq', label: t('colAnswer'), hint: t('hAnswer'), render: (r) => <Answer r={r} /> },
            { key: 'entry', label: t('colScaleIn'), right: true, render: (r) => num(r.entry_pullback) },
            { key: 'stop', label: 'SL', right: true, render: (r) => num(r.stop) },
            { key: 'tp1', label: 'TP1', right: true, render: (r) => num(r.tp1) },
          ]}
        />
      </Section>

      <Section title={t('s9Title')} defaultOpen={false}>
        <DataTable
          label={t('levelsTable')}
          maxH="max-h-[32rem]"
          rows={names
            .filter((s) => !['KILL', 'KILL-S', 'FAIL', 'FAIL-S', 'NO-DATA']
              .includes((views[s]?._stage || {}).stage ?? ''))
            .map((s) => ({ sym: s, px: views[s]?.px_now, lv: views[s]?._levels || {} }))}
          cols={[
            { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
            { key: 'px', label: 'px_now', right: true, render: (r) => num(r.px) },
            { key: 'e20h', label: '1H e20', right: true, render: (r) => num(r.lv.e20_1h) },
            { key: 'vwap', label: '1H vwap', right: true, render: (r) => num(r.lv.vwap_1h) },
            { key: 'e20d', label: 'e20', right: true, render: (r) => num(r.lv.e20d) },
            { key: 'e50d', label: 'e50', right: true, render: (r) => num(r.lv.e50d) },
            { key: 'e200d', label: 'e200', right: true, render: (r) => num(r.lv.e200d) },
            { key: 'atr', label: 'ATR14', right: true, render: (r) => num(r.lv.atr14d) },
            { key: 'hi15', label: 'swingHi15', right: true, render: (r) => num(r.lv.swing_hi15) },
            { key: 'lo10', label: 'swingLo10', right: true, render: (r) => num(r.lv.swing_lo10) },
          ]}
        />
      </Section>

      <Section title={t('s10Title')} defaultOpen={false} subtitle={t('s10Sub')}>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted">Data health</p>
            <ul className="space-y-1">
              {(full.sanity || []).map((s, i) => (
                <li key={i} className="text-xs leading-relaxed text-muted">• {s}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted">{t('headlines', { n: (full.news || []).length })}</p>
            <ul className="max-h-64 space-y-1 overflow-y-auto">
              {(full.news || []).slice(0, 40).map((n, i) => (
                <li key={i} className="text-xs leading-relaxed text-muted">• {n}</li>
              ))}
              {!(full.news || []).length && <li className="text-xs italic text-muted">{t('noNews')}</li>}
            </ul>
          </div>
        </div>
      </Section>

      <Alert status="default">
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Description className="text-xs leading-relaxed">
            <b>{t('limitsTitle')}</b> {t('limitsBody')}
          </Alert.Description>
        </Alert.Content>
      </Alert>
    </div>
  );
}

// ---------------------------------------------------- UIPT-S / UIPT-M ------
// Two modes by holding horizon, per the UIPT_HORIZON spec in the formula file
// (a different thing from stages ending in -S).
const STATE_TONE: Record<string, Tone> = {
  TRIGGERING: { color: 'success', variant: 'primary' },
  COILED: { color: 'warning', variant: 'soft' },
  'IN-TREND': { color: 'accent', variant: 'soft' },
  EXTENDED: { color: 'danger', variant: 'soft' },
};
const STATE_KEY: Record<string, RKey> = {
  TRIGGERING: 'stTriggering', COILED: 'stCoiled', 'IN-TREND': 'stInTrend', EXTENDED: 'stExtended',
};
const FLOW_KEY: Record<string, RKey> = { IN: 'flowIn', OUT: 'flowOut', NEUTRAL: 'flowNeutral' };

function StateChip({ state }: { state?: string }) {
  const t = useT(radarSummary);
  const tone = (state && STATE_TONE[state]) || DEFAULT_TONE;
  const chip = <Chip size="sm" color={tone.color} variant={tone.variant} className="whitespace-nowrap font-semibold">{state ?? '—'}</Chip>;
  const key = state ? STATE_KEY[state] : undefined;
  if (!key) return chip;
  return (
    <Tooltip delay={300}>
      <Tooltip.Trigger>{chip}</Tooltip.Trigger>
      <Tooltip.Content className="text-xs">{t(key)}</Tooltip.Content>
    </Tooltip>
  );
}

/** One card per name: the three answers first (enter now? / from when / latest),
 *  then the price plan. Reads in one screen, no sideways scrolling. */
function PickCard({ r, no, isS }: { r: PackRow; no: number; isS: boolean }) {
  const t = useT(radarSummary);
  const can = r.can_enter_now;
  return (
    <div className={`rounded-xl border-2 px-4 py-3 ${can ? 'border-success/50 bg-success-soft/40' : 'border-separator bg-surface'}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted">#{no}</span>
        <b className="font-mono text-lg">{r.sym}</b>
        <Chip size="sm" variant="soft" color={isS ? 'danger' : 'success'} className="font-bold">{r.horizon}</Chip>
        <StateChip state={r.state} />
        <span className="text-xs text-muted">{r.hold_text}</span>
        <span className="ml-auto text-xs text-muted">
          score <b className="font-mono text-accent">{num(r.score, 2)}</b>
          {r.sector_flow && <> · {r.sector_flow}</>}
        </span>
      </div>

      {/* the three answers */}
      <div className={`mb-2 rounded-lg px-3 py-2 ${can ? 'bg-success-soft' : 'bg-warning-soft'}`}>
        <p className="text-sm font-bold">{can ? '🔥 ' : '⏳ '}{r.verdict_head}</p>
        <p className="mt-0.5 text-xs text-muted">{r.verdict_why}</p>
        <div className="mt-1.5 space-y-0.5 text-xs">
          <p><span className="text-muted">{t('enterFrom')}</span>{' '}<b className="text-success">{r.enter_from}</b></p>
          <p><span className="text-muted">{t('deadline')}</span>{' '}<span>{r.deadline}</span></p>
          {r.confirm_at_both && (
            <p><span className="text-muted">{t('confirmBar')}</span>{' '}<span>{r.confirm_at_both}</span></p>
          )}
        </div>
      </div>

      {/* price plan */}
      <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
        <Cell label={t('enterAboveClose')} value={num(r.entry)} strong />
        <Cell label={t('slExit')} value={num(r.stop)} />
        <Cell label="T1" value={num(r.tp1)} />
        <Cell label="T2" value={num(r.tp2)} />
        <Cell label="R:R (T1/T2)" value={`${num(r.rr1, 2)} / ${num(r.rr2, 2)}`} danger={Number(r.rr1) < 1} />
      </div>
      <p className="mt-2 text-[11px] text-muted">⏱ {r.time_stop_rule}</p>
      {r.rr_warning && <p className="mt-1 text-[11px] text-danger">⚠ {r.rr_warning}</p>}
    </div>
  );
}

function Cell({ label, value, strong, danger }: {
  label: string; value: string; strong?: boolean; danger?: boolean;
}) {
  return (
    <div className={`rounded-lg border px-2 py-1.5 ${danger ? 'border-danger/40 bg-danger-soft' : 'border-separator bg-surface'}`}>
      <p className="text-[10px] leading-tight text-muted">{label}</p>
      <p className={`font-mono tabular-nums ${strong ? 'text-sm font-bold' : ''} ${danger ? 'text-danger' : ''}`}>{value}</p>
    </div>
  );
}

function HorizonSection({ pack }: { pack?: HorizonPack }) {
  const t = useT(radarSummary);
  const [showRejected, setShowRejected] = useState(false);
  if (!pack) {
    return (
      <Card className="rounded-2xl">
        <h3 className="text-sm font-bold">UIPT-S / UIPT-M</h3>
        <p className="text-xs text-warning">{t('hzMissing')}</p>
      </Card>
    );
  }
  const isS = pack.mode === 's';
  const n = isS ? '⑨' : '⑧';
  const title = isS
    ? t('hzTitleS', { n, label: pack.label, x: pack.x })
    : t('hzTitleM', { n, label: pack.label, x: pack.x });
  const picks = pack.picks || [];

  return (
    <Card className={`rounded-2xl border-2 ${isS ? 'border-danger/30' : 'border-success/30'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold">{title}</h3>
        <span className="text-xs text-muted">
          {t('hzRisk', { a: pack.risk_pct?.[0] ?? '—', b: pack.risk_pct?.[1] ?? '—', n: pack.max_concurrent ?? '—' })}
        </span>
      </div>
      <p className="text-xs text-muted">{isS ? t('hzStackS') : t('hzStackM')}</p>

      {/* one card per name — the three answers first, no table hunting */}
      <div className="space-y-3">
        {picks.length === 0 && (
          <p className="flex items-center gap-2 text-sm italic text-muted"><Inbox className="size-4" />{t('hzNoPicks')}</p>
        )}
        {picks.map((r, i) => (
          <PickCard key={r.sym} r={r} no={i + 1} isS={isS} />
        ))}
      </div>

      <Disclosure>
        {({ isExpanded }) => (
          <>
            <Disclosure.Heading>
              <Disclosure.Trigger className="flex items-center gap-1 text-xs text-muted hover:text-foreground">
                {isExpanded ? t('hzHideTable') : t('hzShowTable')}
                <Disclosure.Indicator />
              </Disclosure.Trigger>
            </Disclosure.Heading>
            <Disclosure.Content>
              <div className="mt-2">
                <DataTable
                  label={t('hzTable')}
                  maxH="max-h-[30rem]"
                  rows={picks.map((r, i) => ({ ...r, no: i + 1 }))}
                  empty={t('hzNoPicks')}
                  cols={[
                    { key: 'no', label: '#', hint: t('hRank') },
                    { key: 'sym', label: 'sym', render: (r) => <b className="font-mono text-sm">{r.sym}</b> },
                    { key: 'horizon', label: t('colHoldDW'), hint: t('hHoldDW'),
                      render: (r) => (
                        <span>
                          <Chip size="sm" variant="soft" color={isS ? 'danger' : 'success'} className="font-bold">{r.horizon}</Chip>
                          <div className="mt-0.5 max-w-[11rem] whitespace-normal text-[10px] font-normal text-muted">{r.hold_text}</div>
                        </span>
                      ) },
                    { key: 'state', label: 'state', hint: t('hState'), render: (r) => <StateChip state={r.state} /> },
                    { key: 'stateth', label: t('colMeans'),
                      render: (r) => <span className="text-muted">{r.state && STATE_KEY[r.state] ? t(STATE_KEY[r.state]) : '—'}</span> },
                    { key: 'score', label: 'score', right: true, hint: t('hScore'),
                      render: (r) => <b className="text-accent">{num(r.score, 2)}</b> },
                    { key: 'flow', label: 'sector flow', hint: t('hFlow'),
                      render: (r) => (
                        <span className={r.sector_flow === 'IN' ? 'font-semibold text-success'
                          : r.sector_flow === 'OUT' ? 'text-danger' : 'text-muted'}>
                          {r.sector_flow}{' '}
                          <span className="font-normal text-muted">{r.sector_flow && FLOW_KEY[r.sector_flow] ? t(FLOW_KEY[r.sector_flow]) : ''}</span>
                        </span>
                      ) },
                    { key: 'entry', label: 'entry', hint: t('hEntryRule'), right: true,
                      render: (r) => (
                        <span><b>{num(r.entry)}</b>
                          <div className="text-[10px] font-normal text-muted">{r.entry_rule}</div>
                        </span>
                      ) },
                    { key: 'stop', label: 'SL', right: true, render: (r) => num(r.stop) },
                    { key: 'tp1', label: 'T1', right: true, render: (r) => num(r.tp1) },
                    { key: 'tp2', label: 'T2', right: true, render: (r) => num(r.tp2) },
                    { key: 'rr', label: 'R:R (T1/T2)', right: true, hint: t('hRr'),
                      render: (r) => (
                        <span className={Number(r.rr1) < 1 ? 'font-semibold text-danger' : 'text-success'}>
                          {num(r.rr1, 2)} / {num(r.rr2, 2)}
                        </span>
                      ) },
                    { key: 'wait', label: t('colWait'), hint: t('hWait'),
                      render: (r) => (r.wait_for
                        ? <span className="inline-block max-w-[26rem] whitespace-normal leading-relaxed">{r.wait_for}</span>
                        : <span className="text-muted">—</span>) },
                    { key: 'ts', label: 'time-stop', hint: t('hTimeStop'),
                      render: (r) => <span className="inline-block max-w-[20rem] whitespace-normal text-muted">{r.time_stop_rule}</span> },
                    { key: 'warn', label: t('colCaution'),
                      render: (r) => (r.rr_warning
                        ? <span className="text-danger">{r.rr_warning}</span>
                        : r.phase4_live ? <span className="text-success">{t('p4Live')}</span>
                          : <span className="text-muted">{t('p4Wait')}</span>) },
                  ]}
                />
              </div>
            </Disclosure.Content>
          </>
        )}
      </Disclosure>

      <div>
        <Button size="sm" variant="ghost" className="text-accent" onPress={() => setShowRejected(!showRejected)}>
          {showRejected
            ? t('hideRejected', { n: pack.rejected?.length || 0 })
            : t('showRejected', { n: pack.rejected?.length || 0 })}
        </Button>
        {showRejected && (
          <div className="mt-2">
            <DataTable
              label={t('rejectedTable')}
              maxH="max-h-[24rem]"
              rows={pack.rejected || []}
              empty={t('none')}
              cols={[
                { key: 'sym', label: 'sym', render: (r) => <b className="font-mono">{r.sym}</b> },
                { key: 'score', label: 'score', right: true, render: (r) => num(r.score, 2) },
                { key: 'state', label: 'state' },
                { key: 'failed', label: t('colFailed'), hint: t('hFailed'),
                  render: (r) => <span className="text-danger">{(r.gates_failed || []).join(' · ')}</span> },
              ]}
            />
          </div>
        )}
      </div>

      {(pack.caveats?.length ?? 0) > 0 && (
        <Disclosure>
          <Disclosure.Heading>
            <Disclosure.Trigger className="flex items-center gap-1 text-xs text-muted hover:text-foreground">
              {t('caveats', { n: pack.caveats?.length ?? 0 })}
              <Disclosure.Indicator />
            </Disclosure.Trigger>
          </Disclosure.Heading>
          <Disclosure.Content>
            <ul className="mt-1 space-y-1">
              {pack.caveats?.map((c, i) => (
                <li key={i} className="text-[11px] leading-relaxed text-muted">• {c}</li>
              ))}
            </ul>
          </Disclosure.Content>
        </Disclosure>
      )}
      <p className="text-[11px] text-muted">{isS ? t('hzRuleS') : t('hzRuleM')}</p>
    </Card>
  );
}

function Stat({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${danger ? 'border-danger/40 bg-danger-soft' : 'border-separator bg-surface-secondary'}`}>
      <p className="text-[11px] text-muted">{label}</p>
      <p className={`font-mono font-bold ${danger ? 'text-danger' : ''}`}>{value}</p>
    </div>
  );
}
