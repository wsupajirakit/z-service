import {
  Button, Card, Checkbox, CheckboxGroup, Chip, CloseButton, Disclosure, Label, Switch, ToggleButton, ToggleButtonGroup,
} from '@heroui/react';
import axios from 'axios';
import { Activity, Check, History, Inbox, Sparkles, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useConfirm } from '../components/confirmContext';
import { errorDetail, notify } from '../components/notify';
import { useT, type MessageKey } from '../i18n';
import { stockRadar } from '../i18n/messages/stockRadar';
import { API_BASE, Autocomplete, SYMBOLS, formatTs, renderMarkdown } from '../lib';

type RadarKey = MessageKey<typeof stockRadar>;
type SymbolOption = { symbol: string; name: string; exchange: string };
type ScanResult = { analysis: string };
type HistoryEntry = {
  timestamp: string;
  symbols: SymbolOption[];
  timeframes: string[];
  extended_session: boolean;
  formulas: string[];
  result_markdown: string;
};

const FORMULAS: { id: string; label: RadarKey }[] = [
  { id: 'ADVANCED_VOLUME_ANALYSIS', label: 'fAdvancedVolume' },
  { id: 'IPI', label: 'fIpi' },
  { id: 'IFI', label: 'fIfi' },
  { id: 'UIPT', label: 'fUipt' },
  { id: 'UIPT_HORIZON', label: 'fUiptHorizon' },
  { id: 'EXTENDED_SESSION_ANALYSIS', label: 'fExtended' },
  { id: 'ROLE_CORE_RADAR', label: 'fCoreRadar' },
];
const TIMEFRAMES = ['1W', '1D', '4H', '1H'];

// Markdown from renderMarkdown carries fixed colours; these overrides keep it readable in both themes.
const MD_CLASS = 'text-sm leading-relaxed text-foreground [&_h2]:text-foreground [&_h4]:text-foreground [&_strong]:text-foreground [&_h3]:text-accent';

function readSaved<T>(key: string, fallback: T): T {
  const saved = localStorage.getItem(key);
  return saved ? JSON.parse(saved) : fallback;
}

// Keep the click order of a multi-selection (the backend receives the list as picked).
function keepOrder(prev: string[], next: Iterable<string>): string[] {
  const chosen = new Set(next);
  return [...prev.filter((x) => chosen.has(x)), ...[...chosen].filter((x) => !prev.includes(x))];
}

export function StockRadarView() {
  const t = useT(stockRadar);
  const confirm = useConfirm();
  const [selectedSymbols, setSelectedSymbols] = useState<SymbolOption[]>(() => readSaved('radar_symbols', []));
  const [selectedFormulas, setSelectedFormulas] = useState<string[]>(() => readSaved('radar_formulas', []));
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(() => readSaved('radar_timeframes', ['1D']));
  const [extendedSession, setExtendedSession] = useState<boolean>(() => readSaved('radar_ext', false));
  const [analysisMode, setAnalysisMode] = useState<string>(() => readSaved('radar_mode', 'ai'));

  const [isLoading, setIsLoading] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [tzOffset, setTzOffset] = useState(420);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => { localStorage.setItem('radar_symbols', JSON.stringify(selectedSymbols)); }, [selectedSymbols]);
  useEffect(() => { localStorage.setItem('radar_formulas', JSON.stringify(selectedFormulas)); }, [selectedFormulas]);
  useEffect(() => { localStorage.setItem('radar_timeframes', JSON.stringify(selectedTimeframes)); }, [selectedTimeframes]);
  useEffect(() => { localStorage.setItem('radar_ext', JSON.stringify(extendedSession)); }, [extendedSession]);
  useEffect(() => { localStorage.setItem('radar_mode', JSON.stringify(analysisMode)); }, [analysisMode]);

  const fetchHistory = () => axios.get<HistoryEntry[]>(`${API_BASE}/api/stock_radar/history`)
    .then(res => setHistory(res.data))
    .catch(e => console.error(e));

  useEffect(() => {
    axios.get<HistoryEntry[]>(`${API_BASE}/api/stock_radar/history`)
      .then(res => setHistory(res.data))
      .catch(e => console.error(e));
    axios.get(`${API_BASE}/api/settings/timezone`).then(res => setTzOffset(res.data.offset_minutes)).catch(() => {});
  }, []);

  const handleScan = async () => {
    if (selectedSymbols.length === 0) { notify.warning(t('needSymbol')); return; }
    if (selectedFormulas.length === 0) { notify.warning(t('needFormula')); return; }
    if (selectedTimeframes.length === 0) { notify.warning(t('needTimeframe')); return; }
    if (!(await confirm({ title: t('confirmStartTitle'), body: t('confirmStartBody'), confirmLabel: t('confirmStart'), tone: 'accent' }))) {
      return;
    }

    setIsLoading(true);
    setScanResult(null);
    abortControllerRef.current = new AbortController();
    try {
      const res = await axios.post<ScanResult>(`${API_BASE}/api/stock_radar/scan`, {
        symbols: selectedSymbols,
        formulas: selectedFormulas,
        timeframes: selectedTimeframes,
        extended_session: extendedSession,
        analysis_mode: analysisMode,
      }, {
        signal: abortControllerRef.current.signal,
      });
      setScanResult(res.data);
      void fetchHistory();
    } catch (e) {
      if (axios.isCancel(e)) notify.info(t('stopped'));
      else notify.error(t('scanFailed', { detail: errorDetail(e) }));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = async () => {
    if (await confirm({ title: t('confirmStopTitle'), confirmLabel: t('confirmStop') })) {
      abortControllerRef.current?.abort();
    }
  };

  const canScan = selectedSymbols.length > 0 && selectedFormulas.length > 0 && selectedTimeframes.length > 0;

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-violet-500/15 text-violet-600 dark:text-violet-400">
            <Sparkles className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('description')}</Card.Description>
          </div>
        </Card.Header>

        <Card.Content className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">{t('step1')}</h3>
            <Autocomplete
              value=""
              onChange={() => {}}
              onSelectOption={(opt: SymbolOption) => {
                if (!selectedSymbols.find(s => s.symbol === opt.symbol)) {
                  setSelectedSymbols([...selectedSymbols, opt]);
                }
              }}
              options={SYMBOLS}
              placeholder={t('searchPlaceholder')}
              labelKey="name"
              valueKey="symbol"
            />
            <div className="flex flex-wrap gap-2">
              {selectedSymbols.map((s) => (
                <Chip key={s.symbol} variant="soft" color="accent" className="gap-1 pr-1">
                  <Chip.Label className="font-mono">{s.symbol}</Chip.Label>
                  <CloseButton aria-label={t('remove', { symbol: s.symbol })} className="size-5"
                    onPress={() => setSelectedSymbols(selectedSymbols.filter(sym => sym.symbol !== s.symbol))} />
                </Chip>
              ))}
              {selectedSymbols.length === 0 && <span className="text-sm text-muted">{t('noneSelected')}</span>}
            </div>

            <div className="space-y-3 border-t border-separator pt-4">
              <h3 className="text-sm font-semibold">{t('step2')}</h3>
              <ToggleButtonGroup aria-label={t('timeframes')} selectionMode="multiple"
                selectedKeys={selectedTimeframes}
                onSelectionChange={(keys) => setSelectedTimeframes((prev) => keepOrder(prev, [...keys].map(String)))}>
                {TIMEFRAMES.map((tf, i) => (
                  <ToggleButton key={tf} id={tf} className="min-w-14 font-mono font-semibold">
                    {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                    {tf}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <Switch isSelected={extendedSession} onChange={setExtendedSession}>
                <Switch.Content>
                  <Switch.Control>
                    <Switch.Thumb />
                  </Switch.Control>
                  <span className="text-sm">{t('extended')}</span>
                </Switch.Content>
              </Switch>
            </div>
          </div>

          <div className="space-y-4">
            <CheckboxGroup value={selectedFormulas} onChange={(v) => setSelectedFormulas((prev) => keepOrder(prev, v))}
              className="flex flex-col gap-2">
              <Label className="text-sm font-semibold">{t('step3')}</Label>
              {FORMULAS.map(f => (
                <Checkbox key={f.id} value={f.id}
                  className="rounded-xl border border-separator bg-surface-secondary px-3 py-2.5 transition-colors hover:bg-accent-soft">
                  <Checkbox.Content>
                    <Checkbox.Control>
                      <Checkbox.Indicator />
                    </Checkbox.Control>
                    <span className="text-sm font-medium">{t(f.label)}</span>
                  </Checkbox.Content>
                </Checkbox>
              ))}
            </CheckboxGroup>

            <div className="space-y-3 border-t border-separator pt-4">
              <h3 className="text-sm font-semibold">{t('step4')}</h3>
              <ToggleButtonGroup aria-label={t('mode')} selectionMode="single" disallowEmptySelection fullWidth
                selectedKeys={[analysisMode]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setAnalysisMode(String(next)); }}>
                <ToggleButton id="ai" className="flex-1">
                  <Sparkles className="size-4" />{t('modeAi')}
                </ToggleButton>
                <ToggleButton id="logic" className="flex-1">
                  <ToggleButtonGroup.Separator />
                  <Activity className="size-4" />{t('modeLogic')}
                </ToggleButton>
              </ToggleButtonGroup>
            </div>
          </div>
        </Card.Content>

        <Card.Footer className="flex justify-end gap-3 border-t border-separator pt-4">
          {isLoading && (
            <Button variant="danger" onPress={handleStop}>
              <X className="size-4" />{t('stop')}
            </Button>
          )}
          <Button onPress={handleScan} isPending={isLoading} isDisabled={!canScan}>
            {isLoading ? null : <Sparkles className="size-4" />}
            {isLoading ? t('scanning') : t('start')}
          </Button>
        </Card.Footer>
      </Card>

      {scanResult && (
        <Card className="rounded-2xl">
          <Card.Header className="flex flex-row items-center gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-success-soft text-success">
              <Check className="size-5" />
            </span>
            <Card.Title>{t('resultTitle')}</Card.Title>
          </Card.Header>
          <Card.Content>
            <div className={`${MD_CLASS} rounded-xl border border-separator bg-surface-secondary p-4`}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(scanResult.analysis) }} />
          </Card.Content>
        </Card>
      )}

      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-surface-secondary text-muted">
            <History className="size-5" />
          </span>
          <Card.Title>{t('recentTitle')}</Card.Title>
        </Card.Header>
        <Card.Content className="space-y-3">
          {history.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted">
              <Inbox className="size-6" />
              {t('recentEmpty')}
            </div>
          )}
          {history.map((h, i) => (
            <div key={i} className="space-y-3 rounded-xl border border-separator bg-surface-secondary p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex flex-wrap gap-1.5">
                  {h.symbols.map((s, idx) => (
                    <Chip key={idx} size="sm" variant="tertiary" className="font-mono font-semibold">{s.symbol}</Chip>
                  ))}
                </div>
                <Chip size="sm" variant="soft" className="font-mono">{formatTs(h.timestamp, tzOffset)}</Chip>
              </div>
              <div className="flex flex-wrap gap-2">
                <Chip size="sm" variant="soft" color="accent">{t('tf', { list: h.timeframes.join(', ') })}</Chip>
                <Chip size="sm" variant="soft" color="success">{t('ext', { value: h.extended_session ? t('yes') : t('no') })}</Chip>
                <Chip size="sm" variant="soft" color="warning">{t('formulaCount', { n: h.formulas.length })}</Chip>
              </div>
              <Disclosure>
                {({ isExpanded }) => (
                  <>
                    <Disclosure.Heading>
                      <Disclosure.Trigger className="flex items-center gap-1 text-sm font-medium text-accent">
                        {isExpanded ? t('hideResult') : t('viewResult')}
                        <Disclosure.Indicator />
                      </Disclosure.Trigger>
                    </Disclosure.Heading>
                    <Disclosure.Content>
                      <div className={`${MD_CLASS} mt-2 rounded-lg border border-separator bg-surface p-3`}
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(h.result_markdown) }} />
                    </Disclosure.Content>
                  </>
                )}
              </Disclosure>
            </div>
          ))}
        </Card.Content>
      </Card>
    </div>
  );
}
