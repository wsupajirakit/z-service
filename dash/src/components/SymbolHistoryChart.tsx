import { Checkbox, ToggleButton, ToggleButtonGroup } from '@heroui/react';
import {
  CandlestickSeries, ColorType, HistogramSeries, LineSeries, createChart, createSeriesMarkers,
  type DeepPartial, type IChartApi, type ChartOptions, type MouseEventParams, type SeriesMarker, type Time,
} from 'lightweight-charts';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useLang, useT } from '../i18n';
import { widgets } from '../i18n/messages/widgets';
import type { TradeData } from '../lib';
import { useTheme, type Theme } from '../theme';

export interface SymbolHistoryChartProps {
  data: TradeData[];
  interval: string | null;
}

type Indicator = 'RSI' | 'CMF' | 'OBV' | 'RVOL' | 'IPI';
type Row = TradeData & { time: number };

const MAIN_H = 320;
const IND_H = 180;

// Axis text, grid and border colours per theme; the canvas itself stays transparent.
function chartColors(theme: Theme): DeepPartial<ChartOptions> {
  const dark = theme === 'dark';
  return {
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: dark ? '#94a3b8' : '#475569' },
    grid: { vertLines: { color: dark ? '#1e293b' : '#e2e8f0' }, horzLines: { color: dark ? '#1e293b' : '#e2e8f0' } },
    rightPriceScale: { borderColor: dark ? '#334155' : '#cbd5e1' },
    timeScale: { borderColor: dark ? '#334155' : '#cbd5e1' },
  };
}

const OVERLAYS = [
  { key: 'ema20', label: 'EMA 20', color: '#3b82f6', dot: 'bg-blue-500', field: 'EMA_20' },
  { key: 'ema50', label: 'EMA 50', color: '#a855f7', dot: 'bg-purple-500', field: 'EMA_50' },
  { key: 'ema100', label: 'EMA 100', color: '#06b6d4', dot: 'bg-cyan-500', field: 'EMA_100' },
  { key: 'ema200', label: 'EMA 200', color: '#f97316', dot: 'bg-orange-500', field: 'EMA_200' },
  { key: 'vwap', label: 'VWAP', color: '#eab308', dot: 'bg-yellow-500', field: 'VWAP' },
] as const;
type OverlayKey = (typeof OVERLAYS)[number]['key'];

const INDICATORS: Indicator[] = ['IPI', 'RSI', 'CMF', 'OBV', 'RVOL'];

// Sort by time and drop duplicate timestamps (lightweight-charts rejects them).
function toRows(data: TradeData[]): Row[] {
  const sorted = data
    .map((d) => ({ ...d, time: Math.floor(new Date(d.datetime.replace(' ', 'T') + 'Z').getTime() / 1000) }))
    .filter((d) => !isNaN(d.time))
    .sort((a, b) => a.time - b.time);
  const seen = new Set<number>();
  return sorted.filter((d) => (seen.has(d.time) ? false : (seen.add(d.time), true)));
}

// One readout value in a slot of fixed width, right-aligned, so its neighbours never move.
function Field({ label, width, tone = 'text-foreground', children }: {
  label: string, width: string, tone?: string, children: ReactNode,
}) {
  return (
    <span className="inline-flex shrink-0 items-baseline gap-1 text-muted">
      {label}:
      <span className={`inline-block text-right font-semibold ${tone}`} style={{ width }}>{children}</span>
    </span>
  );
}

const IPI_TONE: Record<string, string> = {
  success: 'bg-success-soft text-success-soft-foreground',
  danger: 'bg-danger-soft text-danger-soft-foreground',
  warning: 'bg-warning-soft text-warning-soft-foreground',
  default: 'bg-surface-secondary text-muted',
};

export function SymbolHistoryChart({ data, interval }: SymbolHistoryChartProps) {
  const t = useT(widgets);
  const lang = useLang();
  const loc = lang === 'th' ? 'th-TH' : 'en-US';
  const { theme } = useTheme();
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    ema20: true, ema50: true, ema100: false, ema200: true, vwap: true,
  });
  const [activeInd, setActiveInd] = useState<Indicator>('IPI');

  const mainContainerRef = useRef<HTMLDivElement>(null);
  const indContainerRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);
  const themeRef = useRef(theme);

  const rows = useMemo(() => toRows(data ?? []), [data]);
  // The bar under the crosshair, tied to the data it came from (falls back to the last bar).
  const [hover, setHover] = useState<{ rows: Row[]; row: Row } | null>(null);

  // Theme colours: kept for new charts and applied to the live ones.
  useEffect(() => {
    themeRef.current = theme;
    chartsRef.current.forEach((c) => c.applyOptions(chartColors(theme)));
  }, [theme]);

  useEffect(() => {
    const mainEl = mainContainerRef.current;
    const indEl = indContainerRef.current;
    if (rows.length === 0 || !mainEl || !indEl) return;
    mainEl.innerHTML = '';
    indEl.innerHTML = '';
    const colors = chartColors(themeRef.current);

    // 1. Price chart (its time axis is hidden; the indicator chart below shows it).
    // autoSize: each chart follows its own box (ResizeObserver), never the text above it.
    const mainChart = createChart(mainEl, {
      ...colors,
      autoSize: true,
      timeScale: { ...colors.timeScale, visible: false },
      crosshair: { mode: 0 },
    });
    const candles = mainChart.addSeries(CandlestickSeries, {
      upColor: '#10b981', downColor: '#f43f5e', borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#f43f5e',
    });
    candles.setData(rows.map((d) => ({ time: d.time as Time, open: d.open, high: d.high, low: d.low, close: d.close })));

    for (const o of OVERLAYS) {
      if (!overlays[o.key]) continue;
      mainChart.addSeries(LineSeries, { color: o.color, lineWidth: 2, title: o.label })
        .setData(rows.map((d) => ({ time: d.time as Time, value: d[o.field] || 0 })).filter((d) => d.value !== 0));
    }

    const volume = mainChart.addSeries(HistogramSeries, { color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '' });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
    volume.setData(rows.map((d) => ({
      time: d.time as Time,
      value: d.volume || 0,
      color: d.close >= d.open ? 'rgba(16, 185, 129, 0.18)' : 'rgba(244, 63, 94, 0.18)',
    })));

    // 2. Indicator chart.
    const indChart = createChart(indEl, { ...colors, autoSize: true, crosshair: { mode: 0 } });
    const line = { lineWidth: 1, axisLabelVisible: true } as const;
    if (activeInd === 'IPI') {
      const s = indChart.addSeries(LineSeries, { color: '#64748b', lineWidth: 1, title: 'IPI', lineStyle: 2 });
      s.setData(rows.map((d) => ({ time: d.time as Time, value: d.IPI || 0 })));
      // Every bar of a run gets its dot; only the run's first bar is labelled, so the
      // labels of consecutive bars do not pile up on each other.
      const markers: SeriesMarker<Time>[] = [];
      let previous = '';
      for (const d of rows) {
        const first = d.IPI_Status !== previous;
        if (d.IPI_Status === 'Institutional Accumulation') {
          markers.push({ time: d.time as Time, position: 'aboveBar', color: '#10b981', shape: 'circle', text: first ? 'ACC' : '' });
        } else if (d.IPI_Status === 'Institutional Distribution') {
          markers.push({ time: d.time as Time, position: 'belowBar', color: '#f43f5e', shape: 'circle', text: first ? 'DIST' : '' });
        }
        previous = d.IPI_Status ?? '';
      }
      createSeriesMarkers(s).setMarkers(markers);
      s.createPriceLine({ ...line, price: 0, color: '#64748b', lineStyle: 1 });
      s.createPriceLine({ ...line, price: 50, color: '#94a3b8', lineStyle: 2, title: '+50' });
      s.createPriceLine({ ...line, price: -20, color: '#94a3b8', lineStyle: 2, title: '-20' });
    } else if (activeInd === 'RSI') {
      const s = indChart.addSeries(LineSeries, { color: '#f43f5e', lineWidth: 2, title: 'RSI' });
      s.setData(rows.map((d) => ({ time: d.time as Time, value: d.RSI || 50 })));
      s.createPriceLine({ ...line, price: 70, color: '#64748b', lineStyle: 1, title: '70' });
      s.createPriceLine({ ...line, price: 50, color: '#94a3b8', lineStyle: 2, title: '50' });
      s.createPriceLine({ ...line, price: 30, color: '#64748b', lineStyle: 1, title: '30' });
    } else if (activeInd === 'CMF') {
      const s = indChart.addSeries(LineSeries, { color: '#10b981', lineWidth: 2, title: 'CMF' });
      s.setData(rows.map((d) => ({ time: d.time as Time, value: d.CMF || 0 })));
      s.createPriceLine({ ...line, price: 0, color: '#64748b', lineStyle: 1 });
    } else if (activeInd === 'OBV') {
      indChart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, title: 'OBV' })
        .setData(rows.map((d) => ({ time: d.time as Time, value: d.OBV || 0 })));
    } else {
      const s = indChart.addSeries(HistogramSeries, { title: 'RVOL Dev %' });
      s.setData(rows.map((d) => {
        const val = d.RVOL_Deviation || 0;
        return { time: d.time as Time, value: val, color: val > 50 ? '#10b981' : val > 0 ? '#34d399' : '#f43f5e' };
      }));
      s.createPriceLine({ ...line, price: 0, color: '#64748b', lineStyle: 1 });
      s.createPriceLine({ ...line, price: 50, color: '#94a3b8', lineStyle: 2, title: '+50%' });
    }

    // 3. Keep both time scales in step.
    let syncing = false;
    const mainScale = mainChart.timeScale();
    const indScale = indChart.timeScale();
    mainScale.subscribeVisibleLogicalRangeChange((range) => {
      if (syncing || !range) return;
      syncing = true; indScale.setVisibleLogicalRange(range); syncing = false;
    });
    indScale.subscribeVisibleLogicalRangeChange((range) => {
      if (syncing || !range) return;
      syncing = true; mainScale.setVisibleLogicalRange(range); syncing = false;
    });

    // 4. Crosshair drives the readout above the chart.
    const onMove = (param: MouseEventParams<Time>) => {
      if (!param.time) return;
      const row = rows.find((d) => d.time === param.time);
      if (row) setHover({ rows, row });
    };
    mainChart.subscribeCrosshairMove(onMove);
    indChart.subscribeCrosshairMove(onMove);

    chartsRef.current = [mainChart, indChart];

    return () => {
      chartsRef.current = [];
      mainChart.remove();
      indChart.remove();
    };
  }, [rows, overlays, activeInd]);

  if (!data || data.length === 0) return null;
  const shown: TradeData = (hover && hover.rows === rows ? hover.row : rows[rows.length - 1]) ?? data[data.length - 1];
  const up = shown.close >= shown.open;
  const fmt = (n: number | null | undefined, digits = 2) =>
    n == null ? '-' : n.toLocaleString(loc, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const ipiColor = !shown.IPI_Status ? 'default'
    : shown.IPI_Status === 'Institutional Accumulation' ? 'success'
      : shown.IPI_Status === 'Institutional Distribution' ? 'danger'
        : shown.IPI_Status.includes('N/A') ? 'default' : 'warning';

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-separator bg-surface p-4 text-foreground shadow-sm md:p-5">
      {/* Readout of the bar under the crosshair: always two lines of fixed height, every value in a
          fixed-width slot with tabular digits, so moving the crosshair never reflows the page or
          resizes the chart below (a narrow screen scrolls the lines sideways instead). */}
      <div className="space-y-1 border-b border-separator pb-3 font-mono text-xs tabular-nums">
        <div className="flex h-6 items-center gap-x-4 overflow-x-auto whitespace-nowrap">
          <span className="shrink-0 text-sm font-bold text-accent">
            {t('chartTitle', { tf: interval ? interval.toUpperCase() : t('chartHistoric') })}
          </span>
          <Field label={t('chartTime')} width="19ch">{shown.datetime}</Field>
          <Field label="O" width="9ch" tone={up ? 'text-success' : 'text-danger'}>{fmt(shown.open)}</Field>
          <Field label="H" width="9ch">{fmt(shown.high)}</Field>
          <Field label="L" width="9ch">{fmt(shown.low)}</Field>
          <Field label="C" width="9ch" tone={up ? 'text-success' : 'text-danger'}>{fmt(shown.close)}</Field>
          <Field label={t('chartVol')} width="12ch">{shown.volume?.toLocaleString(loc) ?? '-'}</Field>
        </div>
        <div className="flex h-7 items-center gap-x-4 overflow-x-auto whitespace-nowrap">
          <span title={shown.IPI_Status ?? ''}
            className={`inline-flex w-[34ch] shrink-0 items-center gap-1 truncate rounded-full px-2 py-0.5 ${IPI_TONE[ipiColor]}`}>
            IPI: <span className="truncate font-semibold">{shown.IPI_Status || '-'}</span>
            <span className="ml-auto shrink-0">{shown.IPI !== null ? fmt(shown.IPI, 1) : ''}</span>
          </span>
          <Field label="RVOL" width="6ch" tone="text-accent">{shown.RVOL !== null ? fmt(shown.RVOL) : '-'}</Field>
          <Field label="CMF" width="7ch" tone="text-accent">{shown.CMF !== null ? fmt(shown.CMF, 3) : '-'}</Field>
          <Field label="RSI" width="5ch" tone="text-rose-600 dark:text-rose-400">{shown.RSI !== null ? fmt(shown.RSI, 1) : '-'}</Field>
        </div>
      </div>

      <div className="flex flex-col items-stretch gap-4 md:flex-row">
        {/* Overlay and indicator controls */}
        <div className="flex shrink-0 flex-col gap-3 rounded-xl border border-separator bg-surface-secondary p-3 text-xs md:w-44">
          <span className="font-semibold text-muted">{t('chartOverlays')}</span>
          <div className="flex flex-wrap gap-x-4 gap-y-2 md:flex-col">
            {OVERLAYS.map((o) => (
              <Checkbox key={o.key} isSelected={overlays[o.key]}
                onChange={(on: boolean) => setOverlays((prev) => ({ ...prev, [o.key]: on }))}>
                <Checkbox.Content>
                  <Checkbox.Control><Checkbox.Indicator /></Checkbox.Control>
                  <span className="flex items-center gap-1.5 text-xs">
                    <span className={`inline-block size-2.5 rounded-full ${o.dot}`} />
                    {o.label}
                  </span>
                </Checkbox.Content>
              </Checkbox>
            ))}
          </div>
          <span className="border-t border-separator pt-2 font-semibold text-muted">{t('chartIndicators')}</span>
          <ToggleButtonGroup size="sm" aria-label={t('chartIndicatorGroup')} selectionMode="single" disallowEmptySelection
            className="flex-wrap md:flex-col md:items-stretch" orientation="horizontal"
            selectedKeys={[activeInd]}
            onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setActiveInd(next as Indicator); }}>
            {INDICATORS.map((ind) => (
              <ToggleButton key={ind} id={ind} className="justify-start font-mono">
                {ind === 'RVOL' ? 'RVOL Dev %' : ind}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </div>

        {/* Chart panes */}
        <div className="relative flex min-w-0 flex-1 flex-col gap-1 overflow-hidden rounded-xl border border-separator bg-background p-2">
          <div ref={mainContainerRef} className="relative w-full" style={{ height: MAIN_H }} />
          <div ref={indContainerRef} className="relative w-full" style={{ height: IND_H }} />
        </div>
      </div>
    </div>
  );
}
