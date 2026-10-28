import {
  Alert, Button, Card, Description, Label, ListBox, ProgressBar, Select, ToggleButton, ToggleButtonGroup,
} from '@heroui/react';
import axios from 'axios';
import { Activity, CheckCircle2, Download, FileSpreadsheet, Newspaper, Server, Sigma } from 'lucide-react';
import { useEffect, useRef, useState, type RefObject } from 'react';
import { useConfirm } from '../components/confirmContext';
import { notify } from '../components/notify';
import { useT, type MessageKey } from '../i18n';
import { exportPage } from '../i18n/messages/export';
import { API_BASE, SYMBOLS, allSymbols, type AutomateJob } from '../lib';

type ExportKey = MessageKey<typeof exportPage>;
type Progress = { kind: 'zip' } | { kind: 'part'; tf: string; part: number } | { kind: 'formula' } | null;
type ExportCheck = { available_count: number; missing_count: number; total_in_list: number };

const ALL = 'All Symbols';
const INTERVALS: { id: string; label: ExportKey }[] = [
  { id: '15m', label: 'i15m' },
  { id: '30m', label: 'i30m' },
  { id: '1h', label: 'i1h' },
  { id: '4h', label: 'i4h' },
  { id: '1d', label: 'i1d' },
  { id: '1w', label: 'i1w' },
];
const AUTOMATE_TFS = ['1h', '4h', '1d', '1w'] as const;

// Poll the server automate job every 3 s while it runs.
function pollAutomate(pollRef: RefObject<ReturnType<typeof setTimeout> | undefined>, setJob: (job: AutomateJob) => void) {
  clearTimeout(pollRef.current);
  const tick = async () => {
    try {
      const res = await axios.get<AutomateJob>(`${API_BASE}/api/automate/status`);
      setJob(res.data);
      if (res.data?.status === 'running') pollRef.current = setTimeout(tick, 3000);
    } catch {
      /* ignore transient polling errors */
    }
  };
  void tick();
}

const downloadFile = async (url: string, filename: string) => {
  const response = await axios.get(url, { responseType: 'blob' });
  const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = blobUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
};

// iOS Safari (and most mobile browsers) only allow ONE download per user gesture
// and handle blob+`download` poorly, so the multi-file blob flow above silently
// fails or throws on mobile. There we instead navigate to a single server URL
// that already sets Content-Disposition: attachment (the /api/export_zip bundle).
const isMobile = () =>
  typeof navigator !== 'undefined' &&
  /iphone|ipad|ipod|android|mobile/i.test(navigator.userAgent);

const downloadViaUrl = (url: string) => {
  const link = document.createElement('a');
  link.href = url;
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
};

export function ExportView() {
  const t = useT(exportPage);
  const confirm = useConfirm();
  const [watchlists, setWatchlists] = useState<Record<string, unknown[]>>({});
  const [selectedWatchlist, setSelectedWatchlist] = useState(ALL);
  const [selectedCombineWatchlists, setSelectedCombineWatchlists] = useState<string[]>([]);

  const [interval, setInterval] = useState('4h');
  const [loading, setLoading] = useState(false);
  const [loadingFormula, setLoadingFormula] = useState(false);
  const [loadingNews, setLoadingNews] = useState(false);
  const [loadingAll, setLoadingAll] = useState(false);
  const [allProgress, setAllProgress] = useState<Progress>(null);
  // Automate Custom (server-side, fire-and-forget; notifies Telegram on completion)
  const [automateTFs, setAutomateTFs] = useState<string[]>([]);
  const [automateStarting, setAutomateStarting] = useState(false);
  const [automateJob, setAutomateJob] = useState<AutomateJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    axios.get(`${API_BASE}/api/watchlist`)
      .then((res) => setWatchlists(res.data))
      .catch((e) => console.error('Failed to fetch watchlists', e));
  }, []);

  useEffect(() => {
    const ref = pollRef;
    pollAutomate(ref, setAutomateJob);
    return () => clearTimeout(ref.current);
  }, []);

  const listName = () => (selectedCombineWatchlists.length > 0 ? selectedCombineWatchlists.join(',') : selectedWatchlist);

  const handleExportExecute = async () => {
    setLoading(true);
    try {
      const name = listName();
      const listParam = name !== ALL ? `&list_name=${encodeURIComponent(name)}` : '';
      if (isMobile()) {
        // Single ZIP (part1 + part2 + formula): one download, works on iOS Safari.
        downloadViaUrl(`${API_BASE}/api/export_zip?interval=${interval}${listParam}`);
      } else {
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=1${listParam}`, `ztrade_export_${interval}_part1.csv`);
        await downloadFile(`${API_BASE}/api/export?interval=${interval}&part=2${listParam}`, `ztrade_export_${interval}_part2.csv`);
      }
    } catch (err) {
      console.error('Failed to export data', err);
      notify.error(t('errHistory'));
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    const name = listName();
    let check: ExportCheck;
    setLoading(true);
    try {
      const res = await axios.get<ExportCheck>(`${API_BASE}/api/export/check?interval=${interval}&list_name=${encodeURIComponent(name)}`);
      check = res.data;
    } catch (err) {
      console.error(err);
      notify.error(t('errCheck'));
      return;
    } finally {
      setLoading(false);
    }
    const { available_count, missing_count, total_in_list } = check;
    const body = (
      <div className="space-y-2 text-sm">
        <p>{t('confirmHistoryAsk', { interval })}</p>
        {name === ALL ? (
          <p>{t('confirmAllAvailable', { n: available_count })}</p>
        ) : (
          <>
            <p>{t('confirmListTotal', { n: total_in_list })}</p>
            <ul className="list-disc space-y-0.5 pl-5">
              <li>{t('confirmListAvailable', { n: available_count })}</li>
              {missing_count > 0 && <li className="text-warning">{t('confirmListMissing', { n: missing_count })}</li>}
            </ul>
          </>
        )}
      </div>
    );
    if (await confirm({ title: t('confirmHistoryTitle'), body, confirmLabel: t('download'), tone: 'accent' })) {
      await handleExportExecute();
    }
  };

  const handleExportFormula = async () => {
    if (!(await confirm({ title: t('confirmFormulaTitle'), body: t('confirmFormulaBody'), confirmLabel: t('download'), tone: 'accent' }))) return;
    setLoadingFormula(true);
    try {
      if (isMobile()) downloadViaUrl(`${API_BASE}/api/export_formula`);
      else await downloadFile(`${API_BASE}/api/export_formula`, 'ztrade_formula.csv');
    } catch (err) {
      console.error('Failed to export formula', err);
      notify.error(t('errFormula'));
    } finally {
      setLoadingFormula(false);
    }
  };

  const handleExportNews = async () => {
    if (!(await confirm({ title: t('confirmNewsTitle'), body: t('confirmNewsBody'), confirmLabel: t('download'), tone: 'accent' }))) return;
    setLoadingNews(true);
    try {
      if (isMobile()) downloadViaUrl(`${API_BASE}/api/export_news`);
      else await downloadFile(`${API_BASE}/api/export_news`, 'ztrade_news.csv');
    } catch (err) {
      console.error('Failed to export news', err);
      notify.error(t('errNews'));
    } finally {
      setLoadingNews(false);
    }
  };

  const handleExportAll4TF = async () => {
    if (!(await confirm({ title: t('confirmAllTitle'), body: t('confirmAllBody'), confirmLabel: t('download9'), tone: 'accent' }))) return;
    setLoadingAll(true);
    const tfs = ['1h', '4h', '1d', '1w'];
    try {
      const name = listName();
      const listParam = name !== ALL ? `&list_name=${encodeURIComponent(name)}` : '';
      if (isMobile()) {
        // All 9 files (8 exports + formula) bundled into a single ZIP download.
        setAllProgress({ kind: 'zip' });
        downloadViaUrl(`${API_BASE}/api/export_zip?all=true${listParam}`);
        setAllProgress(null);
        setLoadingAll(false);
        return;
      }
      for (const tf of tfs) {
        setAllProgress({ kind: 'part', tf, part: 1 });
        await downloadFile(`${API_BASE}/api/export?interval=${tf}&part=1${listParam}`, `ztrade_export_${tf}_part1.csv`);
        setAllProgress({ kind: 'part', tf, part: 2 });
        await downloadFile(`${API_BASE}/api/export?interval=${tf}&part=2${listParam}`, `ztrade_export_${tf}_part2.csv`);
      }
      // Formula must always be the LAST file in the bundle
      setAllProgress({ kind: 'formula' });
      await downloadFile(`${API_BASE}/api/export_formula`, 'ztrade_formula.csv');
      setAllProgress(null);
    } catch (err) {
      console.error('Failed to export all TF', err);
      notify.error(t('errAll'));
      setAllProgress(null);
    } finally {
      setLoadingAll(false);
    }
  };

  // ----- Automate Custom: trigger a server-side fetch job, poll its status -----
  const selectedTFs = AUTOMATE_TFS.filter((tf) => automateTFs.includes(tf));
  const allTFsSelected = selectedTFs.length === 4;
  const jobRunning = automateJob?.status === 'running';

  const startAutomateCustom = async () => {
    if (selectedTFs.length === 0) { notify.warning(t('automateNeedTf')); return; }
    const body = (
      <div className="space-y-2 text-sm">
        <p>{t('automateConfirmBody', { n: SYMBOLS.length, tfs: selectedTFs.join(', ').toUpperCase() })}</p>
        <p className="text-muted">{t('automateConfirmHint')}</p>
      </div>
    );
    if (!(await confirm({ title: t('automateConfirmTitle'), body, confirmLabel: t('automateGo'), tone: 'accent' }))) return;
    setAutomateStarting(true);
    try {
      await axios.post(`${API_BASE}/api/automate`, {
        timeframes: selectedTFs,
        symbols: allSymbols().map((s) => ({ symbol: s.symbol, exchange: s.exchange })),
        rows: 80,
      });
      pollAutomate(pollRef, setAutomateJob);
    } catch (err) {
      if ((err as { response?: { status?: number } })?.response?.status === 409) {
        notify.warning(t('automateBusy'));
      } else {
        console.error('Failed to start automate', err);
        notify.error(t('automateFailed'));
      }
    } finally {
      setAutomateStarting(false);
    }
  };

  const anyLoading = loading || loadingFormula || loadingNews || loadingAll;
  const progressText = !allProgress ? t('downloading')
    : allProgress.kind === 'zip' ? t('preparingZip')
      : allProgress.kind === 'formula' ? t('progressFormula')
        : t('progressPart', { tf: allProgress.tf, part: allProgress.part });
  const names = Object.keys(watchlists);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400">
            <Download className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('description')}</Card.Description>
          </div>
        </Card.Header>

        <Card.Content className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select fullWidth value={selectedWatchlist} isDisabled={anyLoading}
              onChange={(v) => { if (v != null) setSelectedWatchlist(String(v)); }}>
              <Label>{t('activeList')}</Label>
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Description>{t('activeHint')}</Description>
              <Select.Popover>
                <ListBox>
                  <ListBox.Item id={ALL} textValue={t('allSymbols')}>{t('allSymbols')}<ListBox.ItemIndicator /></ListBox.Item>
                  {names.map((name) => (
                    <ListBox.Item key={name} id={name} textValue={name}>{name}<ListBox.ItemIndicator /></ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>

            <Select fullWidth selectionMode="multiple" isDisabled={anyLoading} placeholder={t('combinePlaceholder')}
              value={selectedCombineWatchlists}
              onChange={(v) => setSelectedCombineWatchlists(Array.isArray(v) ? v.map(String) : [])}>
              <Label>{t('combine')}</Label>
              <Select.Trigger>
                <Select.Value>
                  {selectedCombineWatchlists.length === 0
                    ? t('combinePlaceholder')
                    : t('combineValue', { n: selectedCombineWatchlists.length, names: selectedCombineWatchlists.join(', ') })}
                </Select.Value>
                <Select.ClearButton onClick={() => setSelectedCombineWatchlists([])} aria-label={t('clearCombine')} />
                <Select.Indicator />
              </Select.Trigger>
              <Description>{t('combineHint')}</Description>
              <Select.Popover>
                <ListBox selectionMode="multiple" renderEmptyState={() => <p className="p-2 text-center text-xs text-muted">{t('noWatchlists')}</p>}>
                  {names.map((name) => (
                    <ListBox.Item key={name} id={name} textValue={name}>
                      <span className="truncate font-semibold">{name}</span>
                      <span className="ml-auto text-[11px] text-muted">{t('listCount', { n: watchlists[name]?.length || 0 })}</span>
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
          </div>

          <Select fullWidth value={interval} isDisabled={anyLoading}
            onChange={(v) => { if (v != null) setInterval(String(v)); }}>
            <Label>{t('interval')}</Label>
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {INTERVALS.map((it) => (
                  <ListBox.Item key={it.id} id={it.id} textValue={t(it.label)}>{t(it.label)}<ListBox.ItemIndicator /></ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Button fullWidth variant="secondary" onPress={handleExport} isPending={loading} isDisabled={anyLoading && !loading}>
              {loading ? null : <FileSpreadsheet className="size-4 text-success" />}
              {loading ? t('fetchingHistory') : t('downloadHistory')}
            </Button>
            <Button fullWidth variant="secondary" onPress={handleExportFormula} isPending={loadingFormula} isDisabled={anyLoading && !loadingFormula}>
              {loadingFormula ? null : <Sigma className="size-4 text-accent" />}
              {loadingFormula ? t('fetchingFormula') : t('downloadFormula')}
            </Button>
            <Button fullWidth variant="secondary" onPress={handleExportNews} isPending={loadingNews} isDisabled={anyLoading && !loadingNews}>
              {loadingNews ? null : <Newspaper className="size-4 text-warning" />}
              {loadingNews ? t('fetchingNews') : t('downloadNews')}
            </Button>
          </div>

          <Button fullWidth size="lg" onPress={handleExportAll4TF} isPending={loadingAll} isDisabled={anyLoading && !loadingAll}>
            {loadingAll ? null : <Download className="size-5" />}
            {loadingAll ? progressText : t('downloadAll')}
          </Button>
        </Card.Content>
      </Card>

      {/* Automate Custom: server-side fetch, notifies Telegram on completion */}
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-success-soft text-success">
            <Server className="size-5" />
          </span>
          <div className="min-w-0">
            <Card.Title>{t('automateTitle')}</Card.Title>
            <Card.Description>{t('automateBody', { n: SYMBOLS.length })}</Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t('pickTf')}</span>
            <Button size="sm" variant="ghost" isDisabled={jobRunning}
              onPress={() => setAutomateTFs(allTFsSelected ? [] : [...AUTOMATE_TFS])}>
              {allTFsSelected ? t('clearAll') : t('selectAll')}
            </Button>
          </div>
          <ToggleButtonGroup aria-label={t('pickTf')} selectionMode="multiple" fullWidth isDisabled={jobRunning}
            selectedKeys={automateTFs} onSelectionChange={(keys) => setAutomateTFs([...keys].map(String))}>
            {AUTOMATE_TFS.map((tf, i) => (
              <ToggleButton key={tf} id={tf} className="flex-1 font-mono font-semibold">
                {i > 0 ? <ToggleButtonGroup.Separator /> : null}
                {tf.toUpperCase()}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Button fullWidth size="lg" onPress={startAutomateCustom}
            isPending={automateStarting || jobRunning}
            isDisabled={anyLoading || automateStarting || jobRunning || selectedTFs.length === 0}>
            {automateStarting || jobRunning ? null : <Activity className="size-5" />}
            {automateStarting ? t('automateStarting') : jobRunning ? t('automateRunning') : t('automateStart')}
          </Button>

          {automateJob && automateJob.status !== 'idle' && (
            <>
              {automateJob.status === 'running' && (
                <div className="space-y-2 rounded-xl border border-separator bg-surface-secondary p-4">
                  <ProgressBar aria-label={t('progress')} color="success" value={automateJob.current}
                    minValue={0} maxValue={automateJob.total || 1}
                    valueLabel={<span className="font-mono">{automateJob.current}/{automateJob.total}</span>}>
                    <Label className="text-sm">
                      {t('fetchingNow', { tf: automateJob.current_tf?.toUpperCase() ?? '', symbol: automateJob.current_symbol ?? '' })}
                    </Label>
                    <ProgressBar.Output />
                    <ProgressBar.Track>
                      <ProgressBar.Fill />
                    </ProgressBar.Track>
                  </ProgressBar>
                </div>
              )}
              {automateJob.status === 'done' && (
                <Alert status="success">
                  <Alert.Indicator><CheckCircle2 className="size-5" /></Alert.Indicator>
                  <Alert.Content>
                    <Alert.Description>
                      {t('done', {
                        tfs: automateJob.timeframes.map((tf) => tf.toUpperCase()).join(', '),
                        failed: automateJob.failed.length > 0 ? t('failedCount', { n: automateJob.failed.length }) : '',
                      })}
                    </Alert.Description>
                  </Alert.Content>
                </Alert>
              )}
              {automateJob.status === 'error' && (
                <Alert status="danger">
                  <Alert.Indicator />
                  <Alert.Content>
                    <Alert.Description>{t('jobError', { message: automateJob.message })}</Alert.Description>
                  </Alert.Content>
                </Alert>
              )}
            </>
          )}
        </Card.Content>
      </Card>
    </div>
  );
}
