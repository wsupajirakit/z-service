import {
  Alert, Button, Card, Chip, Description, EmptyState, Label, ListBox, Modal, Popover, SearchField, Select, Spinner, Switch,
  Table, ToggleButton, ToggleButtonGroup,
} from '@heroui/react';
import axios from 'axios';
import { ArrowLeft, ChevronRight, Clock, HardDrive, History, Inbox, Layers, LayoutGrid, Send, Settings2, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { ListAvatar } from '../components/ListAvatar';
import { SymbolPicker, type PickerSymbol } from '../components/SymbolPicker';
import { notify } from '../components/notify';
import { Pager } from '../components/Pager';
import { usePaged } from '../components/paging';
import { SectionHeader } from '../components/SectionHeader';
import { useT } from '../i18n';
import { history as messages } from '../i18n/messages/history';
import {
  API_BASE, ConfirmationModal, ResultTable, SymbolHistoryChart, TIMEZONE_OPTIONS, formatTs, type HistorySummary, type TradeData,
} from '../lib';

type SubTab = 'symbol' | 'round';
type Dest = { dest_stock_drive: boolean; dest_stock_telegram: boolean; dest_gold_drive: boolean; dest_gold_telegram: boolean };
type Round = { id: string; timestamp: string; interval: string; extended_session: boolean; records: HistorySummary[] };

const INTERVAL_ORDER = ['15m', '30m', '1h', '4h', '1d', '1w'];
const sortIntervals = (arr: string[]) => [...arr].sort((a, b) => {
  const idxA = INTERVAL_ORDER.indexOf(a.toLowerCase());
  const idxB = INTERVAL_ORDER.indexOf(b.toLowerCase());
  if (idxA === -1) return 1;
  if (idxB === -1) return -1;
  return idxA - idxB;
});
const newestFirst = (a: HistorySummary, b: HistorySummary) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();

// One colour per timeframe so rounds read at a glance (full class strings for Tailwind).
const INTERVAL_TINT: Record<string, string> = {
  '15m': 'bg-pink-500/15 text-pink-700 dark:text-pink-300',
  '30m': 'bg-rose-500/15 text-rose-700 dark:text-rose-300',
  '1h': 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  '4h': 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  '1d': 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  '1w': 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
};

function IntervalChip({ iv }: { iv: string }) {
  return (
    <span className={`inline-flex min-w-10 justify-center rounded-full px-2 py-0.5 font-mono text-xs font-semibold ${INTERVAL_TINT[iv.toLowerCase()] ?? 'bg-surface-secondary text-muted'}`}>
      {iv}
    </span>
  );
}

// Group records into fetch rounds: same interval + session, timestamps within 5 minutes.
function getRounds(list: HistorySummary[]): Round[] {
  const rounds: Round[] = [];
  [...list].sort(newestFirst).forEach((record) => {
    const recordTime = new Date(record.timestamp).getTime();
    const match = rounds.find((r) => r.interval === record.interval && r.extended_session === record.extended_session
      && r.records.some((rec) => Math.abs(new Date(rec.timestamp).getTime() - recordTime) <= 5 * 60 * 1000));
    if (match) {
      match.records.push(record);
      if (recordTime > new Date(match.timestamp).getTime()) match.timestamp = record.timestamp;
    } else {
      rounds.push({ id: `round-${record.id}`, timestamp: record.timestamp, interval: record.interval, extended_session: record.extended_session, records: [record] });
    }
  });
  return rounds;
}

function Loading({ text }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <Spinner size="lg" />
      {text ? <span className="text-sm font-medium text-muted">{text}</span> : null}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <Card className="rounded-2xl">
      <Card.Content className="flex flex-col items-center gap-2 py-12 text-center text-muted">
        <span className="grid size-12 place-items-center rounded-2xl bg-surface-secondary"><Inbox className="size-6" /></span>
        <p className="text-sm">{text}</p>
      </Card.Content>
    </Card>
  );
}

export function HistoryView() {
  const t = useT(messages);
  const [historyList, setHistoryList] = useState<HistorySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const [subTab, setSubTab] = useState<SubTab>('symbol');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [selectedRoundId, setSelectedRoundId] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<HistorySummary | null>(null);
  const [recordData, setRecordData] = useState<TradeData[]>([]);
  const [recordLoading, setRecordLoading] = useState(false);

  const [chartInterval, setChartInterval] = useState<string | null>(null);
  const [selectedPullId, setSelectedPullId] = useState<number | null>(null);
  const [chartRecordData, setChartRecordData] = useState<TradeData[]>([]);
  const [chartLoading, setChartLoading] = useState(false);

  // Display timezone (fixed UTC offset in minutes), shared with Telegram via the server.
  const [tzOffset, setTzOffset] = useState<number>(420);
  const [savingTz, setSavingTz] = useState(false);

  // Output destinations for finished jobs (stored server-side; shared with auto jobs).
  const [dest, setDest] = useState<Dest>({
    dest_stock_drive: true, dest_stock_telegram: true, dest_gold_drive: true, dest_gold_telegram: true,
  });
  const [confirmClear, setConfirmClear] = useState(false);
  const [query, setQuery] = useState('');

  const fetchHistory = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const res = await axios.get(`${API_BASE}/api/history`, { timeout: 15000 });
      setHistoryList(res.data);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  // History, timezone and destinations, loaded in parallel.
  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE}/api/history`, { timeout: 15000 });
        setHistoryList(res.data);
      } catch {
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    })();
    void (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/settings/timezone`);
        if (typeof res.data?.offset_minutes === 'number') setTzOffset(res.data.offset_minutes);
      } catch { /* keep the default (UTC+7) if the setting can't be loaded */ }
    })();
    void (async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/settings/destinations`);
        setDest((d) => ({ ...d, ...res.data }));
      } catch { /* keep defaults (all on) */ }
    })();
  }, []);

  const toggleDest = async (key: keyof Dest) => {
    const next = { ...dest, [key]: !dest[key] };
    setDest(next); // optimistic
    try {
      await axios.post(`${API_BASE}/api/settings/destinations`, { [key]: next[key] });
    } catch (err) {
      console.error('Failed to save destination', err);
      setDest(dest); // revert
      notify.error(t('saveDestFailed'));
    }
  };

  const handleTimezoneChange = async (offset: number) => {
    const opt = TIMEZONE_OPTIONS.find((o) => o.offset === offset);
    const prev = tzOffset;
    setTzOffset(offset); // optimistic
    setSavingTz(true);
    try {
      await axios.post(`${API_BASE}/api/settings/timezone`, {
        offset_minutes: offset,
        label: opt?.label ?? `UTC${offset >= 0 ? '+' : ''}${offset / 60}`,
      });
    } catch (err) {
      console.error('Failed to save timezone', err);
      setTzOffset(prev); // revert on failure
      notify.error(t('saveTzFailed'));
    } finally {
      setSavingTz(false);
    }
  };

  const handleClearHistoryExecute = async () => {
    try {
      await axios.delete(`${API_BASE}/api/history`);
      void fetchHistory();
      setSelectedSymbol(null);
      setSelectedRoundId(null);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  const fetchRecordDetail = async (record: HistorySummary) => {
    setRecordLoading(true);
    setSelectedRecord(record);
    try {
      const res = await axios.get(`${API_BASE}/api/history/${record.id}`);
      setRecordData([...res.data].reverse());
    } catch {
      notify.error(t('recordFailed'));
    } finally {
      setRecordLoading(false);
    }
  };

  const fetchChartRecordDetail = async (id: number) => {
    setChartLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/history/${id}`);
      setChartRecordData([...res.data].reverse());
    } catch {
      notify.error(t('chartFailed'));
    } finally {
      setChartLoading(false);
    }
  };

  // Symbol -> default interval (4h when present) -> newest pull, which loads the chart.
  const pullsFor = (sym: string | null, iv: string | null) =>
    historyList.filter((h) => h.symbol === sym && h.interval === iv).sort(newestFirst);
  const choosePull = (id: number | null) => {
    setSelectedPullId(id);
    if (id) void fetchChartRecordDetail(id);
  };
  const chooseInterval = (sym: string | null, iv: string | null) => {
    setChartInterval(iv);
    choosePull(sym && iv ? (pullsFor(sym, iv)[0]?.id ?? null) : null);
  };
  const chooseSymbol = (sym: string | null) => {
    setSelectedSymbol(sym);
    const intervals = sortIntervals(Array.from(new Set(historyList.filter((h) => h.symbol === sym).map((r) => r.interval))));
    chooseInterval(sym, sym && intervals.length > 0 ? (intervals.includes('4h') ? '4h' : intervals[0]) : null);
  };

  const symbolRecords = historyList.filter((h) => h.symbol === selectedSymbol);
  const availableIntervals = sortIntervals(Array.from(new Set(symbolRecords.map((r) => r.interval))));
  const sortedPulls = pullsFor(selectedSymbol, chartInterval);
  const needle = query.trim().toUpperCase();
  const allSymbols = Array.from(new Set(historyList.map((h) => h.symbol))).sort();
  const uniqueSymbols = allSymbols.filter((sym) => !needle || sym.includes(needle));
  const allRounds = getRounds(historyList);
  const rounds = allRounds.filter((r) => !needle || r.records.some((rec) => rec.symbol.includes(needle)));
  const selectedRound = allRounds.find((r) => r.id === selectedRoundId);
  const roundRecords = (selectedRound?.records ?? []).filter((rec) => !needle || rec.symbol.includes(needle));
  // The fetch round of what is on screen: its symbols are the ones offered for switching.
  const roundOf = (recordId: number | null | undefined) =>
    recordId == null ? undefined : allRounds.find((r) => r.records.some((rec) => rec.id === recordId));
  const symbolsOf = (round: Round | undefined): PickerSymbol[] => {
    const seen = new Map<string, string>();
    for (const rec of round?.records ?? []) if (!seen.has(rec.symbol)) seen.set(rec.symbol, rec.exchange);
    return [...seen].map(([symbol, exchange]) => ({ symbol, exchange })).sort((a, b) => a.symbol.localeCompare(b.symbol));
  };
  const pullRound = roundOf(selectedPullId);
  const dialogRound = roundOf(selectedRecord?.id);
  const switchChartSymbol = (sym: string) => {
    const rec = pullRound?.records.find((r) => r.symbol === sym);
    if (!rec) { chooseSymbol(sym); return; }
    setSelectedSymbol(sym);
    setChartInterval(rec.interval);
    choosePull(rec.id);
  };
  const switchDialogSymbol = (sym: string) => {
    const rec = dialogRound?.records.find((r) => r.symbol === sym);
    if (rec) void fetchRecordDetail(rec);
  };
  const symbolPages = usePaged(uniqueSymbols, 24);
  const roundPages = usePaged(rounds, 25);
  const recordPages = usePaged(roundRecords, 50);
  const tzLabel = TIMEZONE_OPTIONS.find((o) => o.offset === tzOffset)?.label ?? `UTC${tzOffset >= 0 ? '+' : ''}${tzOffset / 60}`;
  const pullCount = (sym: string) => historyList.filter((h) => h.symbol === sym).length;

  const switchTab = (key: SubTab) => {
    chooseSymbol(null);
    setSelectedRoundId(null);
    setSubTab(key);
  };

  const destRows = [
    { label: t('destStock'), drive: 'dest_stock_drive', tg: 'dest_stock_telegram' },
    { label: t('destGold'), drive: 'dest_gold_drive', tg: 'dest_gold_telegram' },
  ] as const;

  const settings = (
    <Popover>
      <Button size="sm" variant="secondary"><Settings2 className="size-4" />{t('settings')}</Button>
      <Popover.Content placement="bottom end" className="w-[22rem]">
        <Popover.Dialog className="space-y-4">
          <div>
            <Popover.Heading className="font-semibold">{t('settings')}</Popover.Heading>
            <p className="text-xs text-muted">{t('settingsDesc')}</p>
          </div>
          {/* Timezone: applies to this page and to Telegram notifications */}
          <Select fullWidth value={tzOffset} isDisabled={savingTz}
            onChange={(k) => { if (k !== null) void handleTimezoneChange(Number(k)); }}>
            <Label>{t('timezone')}</Label>
            <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
            <Description>{t('timezoneHelp')}</Description>
            <Select.Popover>
              <ListBox>
                {TIMEZONE_OPTIONS.map((o) => (
                  <ListBox.Item key={o.offset} id={o.offset} textValue={o.label}>{o.label}<ListBox.ItemIndicator /></ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
          {/* Output destinations for finished jobs (server-side, shared with auto jobs) */}
          <div className="space-y-2">
            <div className="text-sm font-medium">{t('destTitle')}</div>
            <div className="divide-y divide-separator rounded-xl border border-separator">
              {destRows.map((row) => (
                <div key={row.drive} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <span className="text-sm font-semibold">{row.label}</span>
                  <div className="flex items-center gap-4">
                    {([[row.drive, 'Drive', HardDrive], [row.tg, 'Telegram', Send]] as const).map(([key, name, Icon]) => (
                      <Switch key={key} size="sm" isSelected={dest[key]} onChange={() => void toggleDest(key)}>
                        <Switch.Content>
                          <Switch.Control><Switch.Thumb /></Switch.Control>
                          <span className="flex items-center gap-1 text-xs"><Icon className="size-3.5 text-muted" />{name}</span>
                        </Switch.Content>
                      </Switch>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Popover.Dialog>
      </Popover.Content>
    </Popover>
  );

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <Card.Header>
          <SectionHeader icon={History} tint="bg-slate-500/15 text-slate-600 dark:text-slate-300"
            title={t('title')} description={t('description')}
            actions={(
              <div className="flex flex-wrap items-center gap-2">
                {settings}
                {historyList.length > 0 ? (
                  <Button size="sm" variant="danger-soft" onPress={() => setConfirmClear(true)}>
                    <Trash2 className="size-4" />{t('clear')}
                  </Button>
                ) : null}
              </div>
            )} />
        </Card.Header>
        <Card.Content className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <ToggleButtonGroup aria-label={t('tabsLabel')} selectionMode="single" disallowEmptySelection
              selectedKeys={[subTab]} onSelectionChange={(keys) => { const k = [...keys][0]; if (k) switchTab(String(k) as SubTab); }}>
              <ToggleButton id="symbol" className="whitespace-nowrap">
                <LayoutGrid className="size-4" />{t('tabSymbol')}
              </ToggleButton>
              <ToggleButton id="round" className="whitespace-nowrap">
                <ToggleButtonGroup.Separator />
                <Layers className="size-4" />{t('tabRound')}
              </ToggleButton>
            </ToggleButtonGroup>
            <SearchField className="w-full sm:w-64" value={query} onChange={setQuery} aria-label={t('findSymbol')}>
              <SearchField.Group>
                <SearchField.SearchIcon />
                <SearchField.Input placeholder={t('findSymbol')} />
                <SearchField.ClearButton />
              </SearchField.Group>
            </SearchField>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Chip size="sm" variant="soft">{t('statRecords', { n: historyList.length })}</Chip>
            <Chip size="sm" variant="soft">{t('statSymbols', { n: allSymbols.length })}</Chip>
            <Chip size="sm" variant="soft">{t('statRounds', { n: allRounds.length })}</Chip>
            <Chip size="sm" variant="soft" color="accent"><Clock className="size-3" />{t('timesIn', { tz: tzLabel })}</Chip>
          </div>
        </Card.Content>
      </Card>

      {loadError && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content><Alert.Description>{t('loadFailed')}</Alert.Description></Alert.Content>
        </Alert>
      )}

      {subTab === 'symbol' && !selectedSymbol && !loadError && (
        loading ? <Loading /> : uniqueSymbols.length === 0 ? <Empty text={t('empty')} /> : (
          <Card className="rounded-2xl">
            <Card.Content className="space-y-4">
              <div className="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3">
                {symbolPages.pageItems.map((sym) => (
                  <Button key={sym} variant="ghost" aria-label={t('openSymbol', { symbol: sym })} onPress={() => chooseSymbol(sym)}
                    className="group h-auto w-full justify-start gap-3 rounded-2xl border border-separator bg-surface p-3 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
                    <ListAvatar name={sym} />
                    <span className="min-w-0 flex-1">
                      <span className="block font-mono font-bold text-foreground group-hover:text-accent">{sym}</span>
                      <span className="block text-xs font-normal text-muted">{t('pulledTimes', { n: pullCount(sym) })}</span>
                    </span>
                    <ChevronRight className="size-4 text-muted group-hover:text-accent" />
                  </Button>
                ))}
              </div>
              <Pager {...symbolPages} onPage={symbolPages.setPage} onPageSize={symbolPages.setPageSize} sizes={[24, 48, 96, 192]} />
            </Card.Content>
          </Card>
        )
      )}

      {subTab === 'symbol' && selectedSymbol && (
        <div className="space-y-6">
          <Card className="rounded-2xl">
            <Card.Content className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm" variant="ghost" onPress={() => chooseSymbol(null)}>
                  <ArrowLeft className="size-4" />{t('backSymbols')}
                </Button>
                <ListAvatar name={selectedSymbol} />
                <h2 className="text-lg font-bold">{t('symbolTitle', { symbol: selectedSymbol })}</h2>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
                {pullRound ? (
                  <SymbolPicker symbols={symbolsOf(pullRound)} value={selectedSymbol} onChange={switchChartSymbol} />
                ) : null}
                {availableIntervals.length > 0 && (
                  <ToggleButtonGroup size="sm" aria-label={t('intervalFilter')} selectionMode="single" disallowEmptySelection
                    selectedKeys={chartInterval ? [chartInterval] : []}
                    onSelectionChange={(keys) => { const next = [...keys][0]; if (next) chooseInterval(selectedSymbol, String(next)); }}>
                    {availableIntervals.map((tf, i) => (
                      <ToggleButton key={tf} id={tf} className="min-w-12 font-mono font-bold">
                        {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                        {tf.toUpperCase()}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                )}
                {sortedPulls.length > 0 && (
                  <Select className="w-full sm:w-[380px]" value={selectedPullId}
                    onChange={(k) => { if (k !== null) choosePull(Number(k)); }}>
                    <Label>{t('pullSelect')}</Label>
                    <Select.Trigger><Select.Value className="font-mono text-xs" /><Select.Indicator /></Select.Trigger>
                    <Select.Popover>
                      <ListBox>
                        {sortedPulls.map((pull) => {
                          const text = `${formatTs(pull.timestamp, tzOffset)} (${pull.exchange} ${pull.extended_session ? t('withExt') : t('rthOnly')})`;
                          return (
                            <ListBox.Item key={pull.id} id={pull.id} textValue={text}>
                              <span className="font-mono text-xs">{text}</span><ListBox.ItemIndicator />
                            </ListBox.Item>
                          );
                        })}
                      </ListBox>
                    </Select.Popover>
                  </Select>
                )}
              </div>
            </Card.Content>
          </Card>

          {chartLoading ? (
            <Card className="rounded-2xl"><Card.Content><Loading text={t('chartLoading')} /></Card.Content></Card>
          ) : chartRecordData.length > 0 ? (
            <div className="space-y-6">
              <SymbolHistoryChart data={chartRecordData} interval={chartInterval} />
              <div className="space-y-3">
                <h3 className="text-base font-semibold">{t('rawTable')}</h3>
                <ResultTable data={chartRecordData} />
              </div>
            </div>
          ) : <Empty text={t('noRoundData')} />}
        </div>
      )}

      {subTab === 'round' && !selectedRoundId && !loadError && (
        loading ? <Loading /> : rounds.length === 0 ? <Empty text={t('empty')} /> : (
          <Card className="rounded-2xl">
            <Card.Content className="space-y-3 p-0 pb-3">
              <Table>
                <Table.ScrollContainer className="overflow-auto">
                  <Table.Content aria-label={t('roundsLabel')} className="min-w-[860px] text-sm">
                    <Table.Header className="sticky top-0 z-10">
                      <Table.Column isRowHeader>{t('colLatest')}</Table.Column>
                      <Table.Column>{t('colInterval')}</Table.Column>
                      <Table.Column>{t('colExtend')}</Table.Column>
                      <Table.Column className="text-right">{t('colCount')}</Table.Column>
                      <Table.Column>{t('colSymbols')}</Table.Column>
                      <Table.Column className="text-right"><span className="sr-only">{t('colActions')}</span></Table.Column>
                    </Table.Header>
                    <Table.Body items={roundPages.pageItems}>
                      {(r) => (
                        <Table.Row id={r.id}>
                          <Table.Cell className="whitespace-nowrap font-mono text-xs font-semibold">{formatTs(r.timestamp, tzOffset)}</Table.Cell>
                          <Table.Cell><IntervalChip iv={r.interval} /></Table.Cell>
                          <Table.Cell>
                            <Chip size="sm" variant="soft" color={r.extended_session ? 'success' : 'default'}>{r.extended_session ? t('yes') : t('no')}</Chip>
                          </Table.Cell>
                          <Table.Cell className="text-right font-mono font-bold">{r.records.length}</Table.Cell>
                          <Table.Cell>
                            <div className="flex max-w-md flex-wrap items-center gap-1">
                              {r.records.slice(0, 6).map((rec) => (
                                <span key={rec.id} className="rounded-md bg-surface-secondary px-1.5 py-0.5 font-mono text-[11px] text-foreground">{rec.symbol}</span>
                              ))}
                              {r.records.length > 6 ? (
                                <span className="text-[11px] font-medium text-muted">{t('moreSymbols', { n: r.records.length - 6 })}</span>
                              ) : null}
                            </div>
                          </Table.Cell>
                          <Table.Cell className="text-right">
                            <Button size="sm" variant="tertiary" onPress={() => setSelectedRoundId(r.id)}>
                              {t('open')}<ChevronRight className="size-4" />
                            </Button>
                          </Table.Cell>
                        </Table.Row>
                      )}
                    </Table.Body>
                  </Table.Content>
                </Table.ScrollContainer>
              </Table>
              <div className="px-4">
                <Pager {...roundPages} onPage={roundPages.setPage} onPageSize={roundPages.setPageSize} />
              </div>
            </Card.Content>
          </Card>
        )
      )}

      {subTab === 'round' && selectedRoundId && selectedRound && (
        <div className="space-y-6">
          <Card className="rounded-2xl">
            <Card.Content className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div className="flex flex-wrap items-center gap-3">
                <Button size="sm" variant="ghost" onPress={() => setSelectedRoundId(null)}>
                  <ArrowLeft className="size-4" />{t('backRounds')}
                </Button>
                <h2 className="text-lg font-bold">{t('roundTitle')}</h2>
                <span className="font-mono text-xs text-muted">{formatTs(selectedRound.timestamp, tzOffset)}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <IntervalChip iv={selectedRound.interval} />
                <Chip size="sm" variant="soft" color={selectedRound.extended_session ? 'success' : 'default'}>
                  {t('roundExtend', { v: selectedRound.extended_session ? t('yes') : t('no') })}
                </Chip>
                <Chip size="sm" variant="soft">{t('roundTotal', { n: selectedRound.records.length })}</Chip>
              </div>
            </Card.Content>
          </Card>
          <Card className="rounded-2xl">
            <Card.Content className="space-y-3 p-0 pb-3">
              <Table>
                <Table.ScrollContainer className="overflow-auto">
                  <Table.Content aria-label={t('recordsLabel')} className="min-w-[560px] text-sm">
                    <Table.Header className="sticky top-0 z-10">
                      <Table.Column isRowHeader>{t('colSymbol')}</Table.Column>
                      <Table.Column>{t('colExchange')}</Table.Column>
                      <Table.Column>{t('colSaved')}</Table.Column>
                      <Table.Column className="text-right"><span className="sr-only">{t('colActions')}</span></Table.Column>
                    </Table.Header>
                    <Table.Body items={recordPages.pageItems} renderEmptyState={() => (
                      <EmptyState className="py-8 text-center text-sm text-muted">{t('empty')}</EmptyState>
                    )}>
                      {(record) => (
                        <Table.Row id={record.id}>
                          <Table.Cell>
                            <span className="flex items-center gap-2"><ListAvatar name={record.symbol} size="sm" /><span className="font-mono font-bold">{record.symbol}</span></span>
                          </Table.Cell>
                          <Table.Cell className="text-muted">{record.exchange}</Table.Cell>
                          <Table.Cell className="font-mono text-xs text-muted">{formatTs(record.timestamp, tzOffset)}</Table.Cell>
                          <Table.Cell className="text-right">
                            <Button size="sm" variant="tertiary" onPress={() => void fetchRecordDetail(record)}>
                              {t('viewResult')}<ChevronRight className="size-4" />
                            </Button>
                          </Table.Cell>
                        </Table.Row>
                      )}
                    </Table.Body>
                  </Table.Content>
                </Table.ScrollContainer>
              </Table>
              <div className="px-4">
                <Pager {...recordPages} onPage={recordPages.setPage} onPageSize={recordPages.setPageSize} sizes={[50, 100, 200, 500]} />
              </div>
            </Card.Content>
          </Card>
        </div>
      )}

      {/* One stored fetch: chart + table */}
      <Modal.Backdrop isOpen={selectedRecord !== null}
        onOpenChange={(open) => { if (!open) { setSelectedRecord(null); setRecordData([]); } }}>
        <Modal.Container size="cover" scroll="inside">
          <Modal.Dialog>
            <Modal.CloseTrigger />
            <Modal.Header className="flex flex-row flex-wrap items-center gap-3 border-b border-separator pb-4">
              {selectedRecord ? <ListAvatar name={selectedRecord.symbol} size="lg" /> : null}
              <div className="min-w-0 flex-1">
                <Modal.Heading className="flex flex-wrap items-baseline gap-x-2 text-xl">
                  <span className="font-mono font-bold">{selectedRecord?.symbol}</span>
                  <span className="text-base font-normal text-muted">{selectedRecord?.exchange}</span>
                </Modal.Heading>
                <p className="text-xs text-muted">{t('recordDesc')}</p>
              </div>
              {selectedRecord && dialogRound ? (
                <SymbolPicker symbols={symbolsOf(dialogRound)} value={selectedRecord.symbol} onChange={switchDialogSymbol} />
              ) : null}
              {selectedRecord ? (
                <div className="flex flex-wrap items-center gap-2">
                  <IntervalChip iv={selectedRecord.interval} />
                  <Chip size="sm" variant="soft" color={selectedRecord.extended_session ? 'success' : 'default'}>
                    {selectedRecord.extended_session ? t('withExt') : t('rthOnly')}
                  </Chip>
                  <Chip size="sm" variant="soft"><Clock className="size-3" />{formatTs(selectedRecord.timestamp, tzOffset)}</Chip>
                  <Chip size="sm" variant="soft" className="font-mono">ID {selectedRecord.id}</Chip>
                </div>
              ) : null}
            </Modal.Header>
            <Modal.Body className="space-y-6 pt-4">
              {recordLoading ? <Loading text={t('recordLoading')} /> : (
                <>
                  <SymbolHistoryChart data={recordData} interval={selectedRecord?.interval ?? null} />
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">{t('rawTable')}</h3>
                    <ResultTable data={recordData} height="max-h-[55vh]" />
                  </div>
                </>
              )}
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>

      <ConfirmationModal
        isOpen={confirmClear}
        title={t('clearTitle')}
        message={t('clearBody')}
        confirmText={t('clearConfirm')}
        type="danger"
        onConfirm={() => void handleClearHistoryExecute()}
        onCancel={() => setConfirmClear(false)}
      />
    </div>
  );
}
