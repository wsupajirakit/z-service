import {
  Button, Card, Chip, Disclosure, FieldError, Input, Label, ListBox, Modal, Select, Table, Tabs, TextField,
} from '@heroui/react';
import axios from 'axios';
import { ArrowDownRight, ArrowUpRight, FolderPlus, History, Inbox, Pencil, Plus, Wallet, type LucideIcon } from 'lucide-react';
import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { errorDetail, notify } from '../components/notify';
import { useLang, useT } from '../i18n';
import { common } from '../i18n/messages/common';
import { portfolio } from '../i18n/messages/portfolio';
import { API_BASE, SYMBOLS, formatTs } from '../lib';

type SymbolOption = { symbol: string; name: string; exchange: string };
type Position = { symbol: string; total_quantity: number; avg_price: number };
type Transaction = { symbol: string; action: 'buy' | 'sell'; quantity: number; buy_price: number; timestamp: string };
type Portfolio = { positions: Position[]; history: Transaction[] };

const EMPTY: Portfolio = { positions: [], history: [] };

function Section({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: ReactNode }) {
  const t = useT(portfolio);
  const [open, setOpen] = useState(true);
  return (
    <Card className="overflow-hidden rounded-2xl p-0">
      <Disclosure isExpanded={open} onExpandedChange={setOpen}>
        <Disclosure.Heading>
          <Disclosure.Trigger aria-label={t('toggleSection')}
            className="flex w-full items-center gap-3 p-5 text-left transition-colors hover:bg-surface-secondary">
            <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
              <Icon className="size-5" />
            </span>
            <span className="flex-1 text-base font-semibold">{title}</span>
            <Disclosure.Indicator />
          </Disclosure.Trigger>
        </Disclosure.Heading>
        <Disclosure.Content>
          <div className="border-t border-separator p-5">{children}</div>
        </Disclosure.Content>
      </Disclosure>
    </Card>
  );
}

// Asks for a portfolio name (in place of window.prompt).
function NameDialog({ open, title, submitLabel, initial, onClose, onSubmit }: {
  open: boolean; title: string; submitLabel: string; initial: string;
  onClose: () => void; onSubmit: (name: string) => void;
}) {
  const t = useT(portfolio);
  const tc = useT(common);
  const [name, setName] = useState(initial);
  const [touched, setTouched] = useState(false);
  const invalid = touched && !name.trim();
  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    setTouched(true);
    if (name.trim()) onSubmit(name.trim());
  };
  return (
    <Modal.Backdrop isOpen={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <Modal.Container>
        <Modal.Dialog className="sm:max-w-[420px]">
          <Modal.CloseTrigger />
          <form onSubmit={submit}>
            <Modal.Header>
              <Modal.Icon className="bg-accent-soft text-accent-soft-foreground"><Wallet className="size-5" /></Modal.Icon>
              <Modal.Heading>{title}</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <TextField fullWidth autoFocus value={name} onChange={setName} isInvalid={invalid}>
                <Label>{t('nameLabel')}</Label>
                <Input placeholder={t('namePlaceholder')} />
                <FieldError>{t('nameEmpty')}</FieldError>
              </TextField>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="tertiary" onPress={onClose}>{tc('cancel')}</Button>
              <Button type="submit">{submitLabel}</Button>
            </Modal.Footer>
          </form>
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}

export function PortfolioView() {
  const t = useT(portfolio);
  const lang = useLang();
  const money = (n: number) => n.toLocaleString(lang === 'th' ? 'th-TH' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const [portfolios, setPortfolios] = useState<Record<string, Portfolio>>({});
  const [activePortfolio, setActivePortfolio] = useState<string>('Default');

  const [selectedSymbol, setSelectedSymbol] = useState<SymbolOption | null>(null);
  const [action, setAction] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState<number>(1);
  const [buyPrice, setBuyPrice] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [dialog, setDialog] = useState<'new' | 'rename' | null>(null);

  const applyPortfolio = (data: Record<string, Portfolio>) => {
    if (Object.keys(data).length === 0) {
      setPortfolios({ Default: { positions: [], history: [] } });
      setActivePortfolio('Default');
    } else {
      setPortfolios(data);
      setActivePortfolio(prev => data[prev] ? prev : Object.keys(data)[0]);
    }
  };

  const fetchPortfolio = async () => {
    try {
      const res = await axios.get<Record<string, Portfolio>>(`${API_BASE}/api/portfolio`);
      applyPortfolio(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await axios.get<Record<string, Portfolio>>(`${API_BASE}/api/portfolio`);
        if (!alive) return;
        const data = res.data;
        if (Object.keys(data).length === 0) {
          setPortfolios({ Default: { positions: [], history: [] } });
          setActivePortfolio('Default');
        } else {
          setPortfolios(data);
          setActivePortfolio(prev => data[prev] ? prev : Object.keys(data)[0]);
        }
      } catch (e) {
        console.error(e);
      }
    };
    void load();
    return () => { alive = false; };
  }, []);

  const createNewPortfolio = (trimmed: string) => {
    setPortfolios(prev => ({ ...prev, [trimmed]: prev[trimmed] || { positions: [], history: [] } }));
    setActivePortfolio(trimmed);
    setDialog(null);
  };

  const openRename = () => {
    if (activePortfolio === 'Default') { notify.warning(t('cannotRenameDefault')); return; }
    setDialog('rename');
  };

  const renamePortfolio = async (trimmed: string) => {
    setDialog(null);
    if (trimmed === activePortfolio) return;
    try {
      await axios.put(`${API_BASE}/api/portfolio/${encodeURIComponent(activePortfolio)}`, { new_name: trimmed });
      void fetchPortfolio();
    } catch (e) {
      notify.error(t('renameFailed', { detail: errorDetail(e) }));
      console.error(e);
    }
  };

  const handleAdd = async () => {
    if (!selectedSymbol || !buyPrice) { notify.warning(t('needSymbolPrice')); return; }
    if (isNaN(Number(buyPrice)) || Number(buyPrice) <= 0) { notify.warning(t('invalidPrice')); return; }
    if (quantity <= 0) { notify.warning(t('invalidQuantity')); return; }

    setIsLoading(true);
    try {
      await axios.post(`${API_BASE}/api/portfolio`, {
        symbol: selectedSymbol.symbol,
        quantity: parseInt(String(quantity)),
        buy_price: parseFloat(buyPrice),
        action,
        port_name: activePortfolio,
      });
      notify.success(t('added', { action: action === 'buy' ? t('buy') : t('sell'), qty: quantity, symbol: selectedSymbol.symbol }));
      setSelectedSymbol(null);
      setQuantity(1);
      setBuyPrice('');
      setSearchInput('');
      void fetchPortfolio();
    } catch (e) {
      notify.error(t('addFailed', { detail: errorDetail(e) }));
    } finally {
      setIsLoading(false);
    }
  };

  const filteredSymbols = SYMBOLS.filter(s =>
    `${s.symbol} ${s.name}`.toLowerCase().includes(searchInput.toLowerCase()),
  ).slice(0, 10);

  const currentPortfolio = portfolios[activePortfolio] || EMPTY;

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <Card.Header className="flex flex-row flex-wrap items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <Wallet className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <Card.Title>{t('title')}</Card.Title>
            <Card.Description>{t('description')}</Card.Description>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="secondary" onPress={() => setDialog('new')}>
              <FolderPlus className="size-4" />{t('newPortfolio')}
            </Button>
            {activePortfolio !== 'Default' && (
              <Button size="sm" variant="tertiary" onPress={openRename}>
                <Pencil className="size-4" />{t('rename')}
              </Button>
            )}
          </div>
        </Card.Header>
        <Card.Content>
          <Tabs selectedKey={activePortfolio} onSelectionChange={(k) => setActivePortfolio(String(k))}>
            <Tabs.ListContainer>
              <Tabs.List aria-label={t('portfolios')}>
                {Object.keys(portfolios).map(portName => (
                  <Tabs.Tab key={portName} id={portName}>
                    {portName}
                    <Tabs.Indicator />
                  </Tabs.Tab>
                ))}
              </Tabs.List>
            </Tabs.ListContainer>
          </Tabs>
        </Card.Content>
      </Card>

      <Section title={t('addTitle', { name: activePortfolio })} icon={Plus}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <TextField fullWidth value={searchInput} onChange={setSearchInput}>
              <Label>{t('symbol')}</Label>
              <Input placeholder={t('searchSymbol')} />
            </TextField>
            {searchInput && (
              <div className="max-h-48 overflow-y-auto rounded-xl border border-separator bg-surface">
                {filteredSymbols.length === 0 ? (
                  <p className="p-3 text-sm text-muted">{t('noMatch')}</p>
                ) : (
                  <ListBox aria-label={t('searchResults')} selectionMode="none"
                    onAction={(key) => {
                      const s = filteredSymbols.find((x) => x.symbol === key);
                      if (s) { setSelectedSymbol(s); setSearchInput(''); }
                    }}>
                    {filteredSymbols.map(s => (
                      <ListBox.Item key={s.symbol} id={s.symbol} textValue={`${s.symbol} ${s.name}`}>
                        <div className="flex flex-col">
                          <span className="font-mono text-sm font-semibold">{s.symbol}</span>
                          <span className="text-xs text-muted">{s.name}</span>
                        </div>
                      </ListBox.Item>
                    ))}
                  </ListBox>
                )}
              </div>
            )}
            {selectedSymbol && (
              <div className="rounded-xl border border-separator bg-accent-soft p-3 text-accent-soft-foreground">
                <p className="font-mono font-semibold">{selectedSymbol.symbol}</p>
                <p className="text-xs opacity-80">{selectedSymbol.name}</p>
              </div>
            )}
          </div>

          <Select fullWidth value={action} onChange={(v) => { if (v === 'buy' || v === 'sell') setAction(v); }}>
            <Label>{t('action')}</Label>
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id="buy" textValue={t('buy')}>{t('buy')}<ListBox.ItemIndicator /></ListBox.Item>
                <ListBox.Item id="sell" textValue={t('sell')}>{t('sell')}<ListBox.ItemIndicator /></ListBox.Item>
              </ListBox>
            </Select.Popover>
          </Select>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <TextField fullWidth type="number" value={String(quantity)}
            onChange={(v) => setQuantity(Math.max(1, parseInt(v) || 1))}>
            <Label>{t('quantity')}</Label>
            <Input min={1} className="font-mono" />
          </TextField>
          <TextField fullWidth type="number" value={buyPrice} onChange={setBuyPrice}>
            <Label>{t('price')}</Label>
            <Input min={0} step="0.01" className="font-mono" />
          </TextField>
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium">{t('totalCost')}</span>
            <div className="rounded-xl border border-separator bg-surface-secondary px-3 py-2 font-mono font-semibold">
              {buyPrice ? money(Number(buyPrice) * quantity) : money(0)}
            </div>
          </div>
        </div>

        <Button fullWidth className="mt-4" onPress={handleAdd} isPending={isLoading} isDisabled={!selectedSymbol || !buyPrice}>
          {isLoading ? null : <Plus className="size-4" />}
          {isLoading ? t('adding') : t('add')}
        </Button>
      </Section>

      <Section title={t('positionsTitle')} icon={Wallet}>
        <Table variant="secondary">
          <Table.ScrollContainer>
            <Table.Content aria-label={t('positionsTable')} className="min-w-[480px]">
              <Table.Header>
                <Table.Column isRowHeader>{t('symbol')}</Table.Column>
                <Table.Column className="text-right">{t('quantity')}</Table.Column>
                <Table.Column className="text-right">{t('avgPrice')}</Table.Column>
                <Table.Column className="text-right">{t('totalCost')}</Table.Column>
              </Table.Header>
              <Table.Body renderEmptyState={() => (
                <div className="flex flex-col items-center gap-2 py-8 text-sm text-muted">
                  <Inbox className="size-6" />{t('noPositions')}
                </div>
              )}>
                {currentPortfolio.positions.map((pos, idx) => (
                  <Table.Row key={idx}>
                    <Table.Cell className="font-mono font-semibold">{pos.symbol}</Table.Cell>
                    <Table.Cell className="text-right font-mono">{pos.total_quantity}</Table.Cell>
                    <Table.Cell className="text-right font-mono">${money(pos.avg_price)}</Table.Cell>
                    <Table.Cell className="text-right font-mono">${money(pos.total_quantity * pos.avg_price)}</Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Content>
          </Table.ScrollContainer>
        </Table>
      </Section>

      <Section title={t('historyTitle')} icon={History}>
        {currentPortfolio.history.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-sm text-muted">
            <Inbox className="size-6" />{t('noHistory')}
          </div>
        ) : (
          <div className="space-y-2">
            {currentPortfolio.history.map((h, idx) => {
              const buy = h.action === 'buy';
              return (
                <div key={idx} className="flex items-center justify-between gap-3 rounded-xl border border-separator bg-surface-secondary p-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${buy ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'}`}>
                      {buy ? <ArrowDownRight className="size-4" /> : <ArrowUpRight className="size-4" />}
                    </span>
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 font-semibold">
                        <span className="font-mono">{h.symbol}</span>
                        <Chip size="sm" variant="soft" color={buy ? 'success' : 'danger'}>{buy ? t('buy') : t('sell')}</Chip>
                        <span className="font-mono text-sm">{h.quantity} @ ${money(h.buy_price)}</span>
                      </p>
                      <p className="font-mono text-xs text-muted">{formatTs(h.timestamp, 420)}</p>
                    </div>
                  </div>
                  <p className="shrink-0 font-mono font-bold">${money(h.quantity * h.buy_price)}</p>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {dialog === 'new' && (
        <NameDialog open title={t('newTitle')} submitLabel={t('create')} initial=""
          onClose={() => setDialog(null)} onSubmit={createNewPortfolio} />
      )}
      {dialog === 'rename' && (
        <NameDialog open title={t('renameTitle', { name: activePortfolio })} submitLabel={t('renameAction')} initial={activePortfolio}
          onClose={() => setDialog(null)} onSubmit={renamePortfolio} />
      )}
    </div>
  );
}
