import { Button, Card, Chip, CloseButton, Disclosure, Table } from '@heroui/react';
import axios from 'axios';
import { CalendarClock, Check, History, Inbox } from 'lucide-react';
import { useEffect, useState } from 'react';
import { errorDetail, notify } from '../components/notify';
import { useT } from '../i18n';
import { earningScan } from '../i18n/messages/earningScan';
import { API_BASE, Autocomplete, EARNING_SCAN_PROVIDER_LABELS, US_STOCK_SYMBOLS, formatTs } from '../lib';

type SymbolOption = { symbol: string; name: string; exchange: string };
type EarningRow = { period?: string; eps_actual?: number; eps_estimate?: number; surprise_percent?: number };
type Attempt = { provider: string; status: string; detail?: string };
type ScanItem = {
  symbol: string;
  provider?: string;
  next_earnings_date?: string;
  error?: string;
  history?: EarningRow[];
  attempted?: Attempt[];
};
type ScanResult = { results: ScanItem[] };
type HistoryEntry = { timestamp: string; symbols: string[]; results: ScanItem[] };

const providerLabel = (p: string) => EARNING_SCAN_PROVIDER_LABELS[p] || p;

function ResultList({ results }: { results: ScanItem[] }) {
  const t = useT(earningScan);
  return (
    <div className="space-y-3">
      {results.map((r, idx) => (
        <div key={idx} className="space-y-3 rounded-xl border border-separator bg-surface-secondary p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono font-bold">{r.symbol}</span>
            <div className="flex flex-wrap items-center gap-2">
              {r.provider ? (
                <Chip size="sm" variant="soft" color="success">{t('source', { name: providerLabel(r.provider) })}</Chip>
              ) : (
                <Chip size="sm" variant="soft" color="danger">{t('noDataChip')}</Chip>
              )}
              {r.next_earnings_date && (
                <Chip size="sm" variant="soft" color="accent">
                  <CalendarClock className="size-3" />
                  <Chip.Label>{t('next', { date: r.next_earnings_date })}</Chip.Label>
                </Chip>
              )}
            </div>
          </div>

          {r.error && <p className="text-sm text-danger">{r.error}</p>}

          {r.history && r.history.length > 0 && (
            <Table variant="secondary">
              <Table.ScrollContainer>
                <Table.Content aria-label={t('historyTable', { symbol: r.symbol })} className="min-w-[420px]">
                  <Table.Header>
                    <Table.Column isRowHeader>{t('period')}</Table.Column>
                    <Table.Column className="text-right">{t('epsActual')}</Table.Column>
                    <Table.Column className="text-right">{t('epsEstimate')}</Table.Column>
                    <Table.Column className="text-right">{t('surprise')}</Table.Column>
                  </Table.Header>
                  <Table.Body>
                    {r.history.map((h, hIdx) => {
                      const s = h.surprise_percent;
                      const tone = s != null && s > 0 ? 'text-success' : s != null && s < 0 ? 'text-danger' : '';
                      return (
                        <Table.Row key={hIdx}>
                          <Table.Cell>{h.period ?? '-'}</Table.Cell>
                          <Table.Cell className="text-right font-mono">{h.eps_actual ?? '-'}</Table.Cell>
                          <Table.Cell className="text-right font-mono">{h.eps_estimate ?? '-'}</Table.Cell>
                          <Table.Cell className={`text-right font-mono font-medium ${tone}`}>{s ?? '-'}</Table.Cell>
                        </Table.Row>
                      );
                    })}
                  </Table.Body>
                </Table.Content>
              </Table.ScrollContainer>
            </Table>
          )}

          {r.attempted && r.attempted.length > 0 && (
            <Disclosure>
              <Disclosure.Heading>
                <Disclosure.Trigger className="flex items-center gap-1 text-xs text-muted hover:text-foreground">
                  {t('attempts')}
                  <Disclosure.Indicator />
                </Disclosure.Trigger>
              </Disclosure.Heading>
              <Disclosure.Content>
                <ul className="mt-1 space-y-0.5 text-xs text-muted">
                  {r.attempted.map((a, aIdx) => (
                    <li key={aIdx}>{providerLabel(a.provider)}: {a.status}{a.detail ? ` (${a.detail})` : ''}</li>
                  ))}
                </ul>
              </Disclosure.Content>
            </Disclosure>
          )}
        </div>
      ))}
    </div>
  );
}

export function EarningScanView() {
  const t = useT(earningScan);
  const [selectedSymbols, setSelectedSymbols] = useState<SymbolOption[]>(() => {
    const saved = localStorage.getItem('earning_scan_symbols');
    return saved ? JSON.parse(saved) : [];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [tzOffset, setTzOffset] = useState(420);

  useEffect(() => {
    localStorage.setItem('earning_scan_symbols', JSON.stringify(selectedSymbols));
  }, [selectedSymbols]);

  const fetchHistory = () => axios.get<HistoryEntry[]>(`${API_BASE}/api/earning_scan/history`)
    .then(res => setHistory(res.data))
    .catch(e => console.error(e));

  useEffect(() => {
    axios.get<HistoryEntry[]>(`${API_BASE}/api/earning_scan/history`)
      .then(res => setHistory(res.data))
      .catch(e => console.error(e));
    axios.get(`${API_BASE}/api/settings/timezone`).then(res => setTzOffset(res.data.offset_minutes)).catch(() => {});
  }, []);

  const handleScan = async () => {
    if (selectedSymbols.length === 0) { notify.warning(t('pickFirst')); return; }
    setIsLoading(true);
    setScanResult(null);
    try {
      const res = await axios.post<ScanResult>(`${API_BASE}/api/earning_scan/scan`, {
        symbols: selectedSymbols.map(s => s.symbol),
      });
      setScanResult(res.data);
      notify.success(t('scanDone', { n: res.data.results?.length ?? 0 }));
      void fetchHistory();
    } catch (e) {
      notify.error(t('scanFailed', { detail: errorDetail(e) }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-teal-500/15 text-teal-600 dark:text-teal-400">
            <CalendarClock className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('description')}</Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">{t('pickTitle')}</h3>
            {selectedSymbols.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">{t('selectedCount', { n: selectedSymbols.length })}</span>
                <Button size="sm" variant="ghost" onPress={() => setSelectedSymbols([])}>{t('clearAll')}</Button>
              </div>
            )}
          </div>
          <Autocomplete
            value=""
            onChange={() => {}}
            onSelectOption={(opt: SymbolOption) => {
              if (!selectedSymbols.find(s => s.symbol === opt.symbol)) {
                setSelectedSymbols([...selectedSymbols, opt]);
              }
            }}
            options={US_STOCK_SYMBOLS}
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
        </Card.Content>
        <Card.Footer className="flex justify-end border-t border-separator pt-4">
          <Button onPress={handleScan} isPending={isLoading} isDisabled={selectedSymbols.length === 0}>
            {isLoading ? null : <CalendarClock className="size-4" />}
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
            <ResultList results={scanResult.results} />
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
                  {h.symbols.map((s) => (
                    <Chip key={s} size="sm" variant="tertiary" className="font-mono font-semibold">{s}</Chip>
                  ))}
                </div>
                <Chip size="sm" variant="soft" className="font-mono">{formatTs(h.timestamp, tzOffset)}</Chip>
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
                      <div className="mt-2"><ResultList results={h.results} /></div>
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
