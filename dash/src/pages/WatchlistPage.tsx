import { Button, Chip, Drawer, Input, Label, Modal, SearchField, Spinner, TextField, Tooltip } from '@heroui/react';
import axios from 'axios';
import { ArrowLeft, Check, ListPlus, Pencil, Pin, Plus, SearchX, Star, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useConfirm } from '../components/confirmContext';
import { ListAvatar } from '../components/ListAvatar';
import { splitListName, type ListName } from '../components/listIdentity';
import { errorDetail, notify } from '../components/notify';
import { API_BASE } from '../core';
import { useLang, useT } from '../i18n';
import { common } from '../i18n/messages/common';
import { watchlist as messages } from '../i18n/messages/watchlist';
import { SYMBOLS } from '../symbols';

type WatchItem = { symbol: string; name?: string };
type Lists = Record<string, WatchItem[]>;
type NameDialog = { mode: 'new' | 'rename'; value: string };

const PINNED = ['Default', 'All Symbols'];
const EXCHANGE = new Map(SYMBOLS.map((s) => [s.symbol, s.exchange]));

/** Pinned lists first, then dated lists newest first, then the rest by name. */
function ordered(names: string[]) {
  const key = (n: ListName) => (n.date ? n.date.month * 100 + n.date.day : -1);
  return names
    .filter((n) => !PINNED.includes(n))
    .map((name) => ({ name, parts: splitListName(name) }))
    .sort((a, b) => key(b.parts) - key(a.parts) || a.name.localeCompare(b.name))
    .map((x) => x.name);
}

function useDateLabel() {
  const lang = useLang();
  return useCallback((date: ListName['date']) => {
    if (!date) return '';
    const d = new Date(2000, date.month - 1, date.day);
    return d.toLocaleDateString(lang === 'th' ? 'th-TH' : 'en-US', { day: 'numeric', month: 'short' });
  }, [lang]);
}

function ListRow({ name, count, active, onSelect }: {
  name: string, count: number, active: boolean, onSelect: () => void,
}) {
  const t = useT(messages);
  const dateLabel = useDateLabel();
  const parts = splitListName(name);
  return (
    <Button variant="ghost" fullWidth onPress={onSelect} aria-current={active ? 'true' : undefined}
      className={`h-auto justify-start gap-3 rounded-xl px-2.5 py-2 text-left ${active
        ? 'bg-accent-soft text-accent-soft-foreground ring-1 ring-accent/30' : 'hover:bg-surface-secondary'}`}>
      <ListAvatar name={name} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold" title={name}>{parts.base}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted">
          {t('symbolsCount', { n: count })}
          {parts.date ? <><span aria-hidden>·</span>{dateLabel(parts.date)}</> : null}
        </span>
      </span>
    </Button>
  );
}

function ListsPanel({ lists, active, onSelect, onNew }: {
  lists: Lists, active: string, onSelect: (name: string) => void, onNew: () => void,
}) {
  const t = useT(messages);
  const [query, setQuery] = useState('');
  const names = Object.keys(lists);
  const needle = query.trim().toLowerCase();
  const match = (n: string) => !needle || n.toLowerCase().includes(needle);
  const pinned = PINNED.filter((n) => names.includes(n) && match(n));
  const themed = ordered(names).filter(match);
  const section = (title: string, icon: ReactNode, items: string[]) => (items.length ? (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 px-2.5 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
        {icon}{title}
      </div>
      {items.map((n) => (
        <ListRow key={n} name={n} count={lists[n]?.length ?? 0} active={n === active} onSelect={() => onSelect(n)} />
      ))}
    </div>
  ) : null);
  return (
    <aside className="flex min-h-0 flex-col border-r border-separator bg-surface">
      <div className="space-y-3 border-b border-separator p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="font-semibold">{t('listsLabel')}</h2>
            <p className="text-xs text-muted">{t('listsCount', { n: names.length })}</p>
          </div>
          <Tooltip delay={200}>
            <Button isIconOnly size="sm" variant="secondary" aria-label={t('newList')} onPress={onNew}>
              <ListPlus className="size-4" />
            </Button>
            <Tooltip.Content>{t('newList')}</Tooltip.Content>
          </Tooltip>
        </div>
        <SearchField fullWidth value={query} onChange={setQuery} aria-label={t('findList')}>
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input placeholder={t('findList')} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
      </div>
      <nav aria-label={t('listsLabel')} className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {section(t('pinned'), <Pin className="size-3" />, pinned)}
        {section(t('themed'), <Star className="size-3" />, themed)}
        {!pinned.length && !themed.length ? (
          <p className="px-3 py-8 text-center text-sm text-muted">{t('noListMatch')}</p>
        ) : null}
      </nav>
    </aside>
  );
}

function AddSymbolsDrawer({ open, onOpenChange, list, members, onAdd }: {
  open: boolean, onOpenChange: (open: boolean) => void, list: string,
  members: Set<string>, onAdd: (s: { symbol: string, name: string }) => Promise<void>,
}) {
  const t = useT(messages);
  const tc = useT(common);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const needle = query.trim().toLowerCase();
  const found = useMemo(() => SYMBOLS.filter((s) => !needle || `${s.symbol} ${s.name}`.toLowerCase().includes(needle)), [needle]);
  const add = async (s: { symbol: string, name: string }) => {
    setBusy(s.symbol);
    await onAdd(s);
    setBusy(null);
  };
  return (
    <Drawer.Backdrop isOpen={open} onOpenChange={onOpenChange}>
      <Drawer.Content placement="right" className="w-full sm:max-w-md">
        <Drawer.Dialog className="flex h-full flex-col">
          <Drawer.Header className="space-y-3">
            <div className="flex items-center gap-3">
              <ListAvatar name={list} />
              <div className="min-w-0">
                <Drawer.Heading className="truncate">{t('addTitle', { list })}</Drawer.Heading>
                <p className="text-xs text-muted">{t('addDesc')}</p>
              </div>
            </div>
            <SearchField fullWidth autoFocus value={query} onChange={setQuery} aria-label={t('search')}>
              <SearchField.Group>
                <SearchField.SearchIcon />
                <SearchField.Input placeholder={t('search')} />
                <SearchField.ClearButton />
              </SearchField.Group>
            </SearchField>
            <p className="text-xs text-muted">{t('shown', { n: found.length, total: SYMBOLS.length })}</p>
          </Drawer.Header>
          <Drawer.Body className="min-h-0 flex-1 overflow-y-auto">
            {found.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted"><SearchX className="size-6" />{t('noMatch')}</div>
            ) : (
              <ul className="divide-y divide-separator">
                {found.map((s) => {
                  const inList = members.has(s.symbol);
                  return (
                    <li key={s.symbol} className="flex items-center gap-3 py-2.5">
                      <ListAvatar name={s.symbol} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="font-mono text-sm font-semibold">{s.symbol}</div>
                        <div className="truncate text-xs text-muted">{s.name}</div>
                      </div>
                      {inList ? (
                        <Chip size="sm" color="warning" variant="soft" aria-label={t('inList', { symbol: s.symbol })}>
                          <Star className="size-3 fill-current" />
                        </Chip>
                      ) : (
                        <Button size="sm" variant="secondary" isPending={busy === s.symbol}
                          aria-label={t('addSymbol', { symbol: s.symbol })} onPress={() => void add(s)}>
                          <Plus className="size-4" />
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Drawer.Body>
          <Drawer.Footer>
            <Button slot="close" variant="secondary" fullWidth><Check className="size-4" />{tc('close')}</Button>
          </Drawer.Footer>
        </Drawer.Dialog>
      </Drawer.Content>
    </Drawer.Backdrop>
  );
}

function ListDetail({ name, items, onBack, onRename, onAddOpen, onRemove }: {
  name: string, items: WatchItem[], onBack: () => void, onRename: () => void,
  onAddOpen: () => void, onRemove: (symbol: string) => void,
}) {
  const t = useT(messages);
  const dateLabel = useDateLabel();
  const [filter, setFilter] = useState('');
  const parts = splitListName(name);
  const needle = filter.trim().toLowerCase();
  const shown = items.filter((s) => !needle || `${s.symbol} ${s.name ?? ''}`.toLowerCase().includes(needle));
  return (
    <section className="flex min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-separator bg-background/80 px-4 py-4 backdrop-blur md:px-6">
        <Button isIconOnly size="sm" variant="ghost" className="lg:hidden" aria-label={t('back')} onPress={onBack}>
          <ArrowLeft className="size-5" />
        </Button>
        <ListAvatar name={name} size="lg" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-xl font-semibold" title={name}>{parts.base}</h2>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <Chip size="sm" variant="soft">{t('symbolsCount', { n: items.length })}</Chip>
            {parts.date ? <span>{t('created', { date: dateLabel(parts.date) })}</span> : null}
            <span className="font-mono text-xs">{name}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!PINNED.includes(name) ? (
            <Button size="sm" variant="tertiary" onPress={onRename}><Pencil className="size-4" />{t('rename')}</Button>
          ) : null}
          <Button size="sm" onPress={onAddOpen}><Plus className="size-4" />{t('addSymbols')}</Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        {items.length === 0 ? (
          <div className="mx-auto flex max-w-sm flex-col items-center gap-3 py-16 text-center">
            <span className="grid size-16 place-items-center rounded-2xl bg-surface-secondary text-muted"><Star className="size-7" /></span>
            <p className="font-medium">{t('empty')}</p>
            <p className="text-sm text-muted">{t('emptyHint')}</p>
            <Button onPress={onAddOpen}><Plus className="size-4" />{t('addSymbols')}</Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <SearchField className="w-full sm:max-w-xs" value={filter} onChange={setFilter} aria-label={t('filterMembers')}>
                <SearchField.Group>
                  <SearchField.SearchIcon />
                  <SearchField.Input placeholder={t('filterMembers')} />
                  <SearchField.ClearButton />
                </SearchField.Group>
              </SearchField>
              <span className="text-xs text-muted">{t('shown', { n: shown.length, total: items.length })}</span>
            </div>
            {shown.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted"><SearchX className="size-6" />{t('noMatch')}</div>
            ) : (
              <ul className="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-3">
                {shown.map((s) => (
                  <li key={s.symbol}
                    className="group flex items-center gap-3 rounded-2xl border border-separator bg-surface p-3 shadow-sm transition-shadow hover:shadow-md">
                    <ListAvatar name={s.symbol} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold">{s.symbol}</span>
                        {EXCHANGE.get(s.symbol) ? (
                          <span className="rounded-md bg-surface-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted">{EXCHANGE.get(s.symbol)}</span>
                        ) : null}
                      </div>
                      <div className="truncate text-xs text-muted" title={s.name}>{s.name}</div>
                    </div>
                    <Tooltip delay={200}>
                      <Button isIconOnly size="sm" variant="ghost" aria-label={t('remove')}
                        className="text-muted opacity-60 transition-opacity hover:text-danger group-hover:opacity-100"
                        onPress={() => onRemove(s.symbol)}>
                        <Trash2 className="size-4" />
                      </Button>
                      <Tooltip.Content>{t('remove')}</Tooltip.Content>
                    </Tooltip>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export function WatchlistView() {
  const t = useT(messages);
  const tc = useT(common);
  const confirm = useConfirm();
  const [lists, setLists] = useState<Lists | null>(null);
  const [active, setActive] = useState('Default');
  const [showDetail, setShowDetail] = useState(false); // narrow screens: list or detail
  const [nameDialog, setNameDialog] = useState<NameDialog | null>(null);
  const [adding, setAdding] = useState(false);

  const apply = useCallback((data: Lists) => {
    const next = Object.keys(data).length ? data : { Default: [] };
    setLists(next);
    setActive((prev) => (next[prev] ? prev : Object.keys(next)[0]));
  }, []);

  const reload = useCallback(() => axios.get<Lists>(`${API_BASE}/api/watchlist`)
    .then((res) => apply(res.data))
    .catch((e) => notify.error(t('loadFailed', { detail: errorDetail(e) }))), [apply, t]);

  useEffect(() => {
    let alive = true;
    axios.get<Lists>(`${API_BASE}/api/watchlist`)
      .then((res) => { if (alive) apply(res.data); })
      .catch(() => { if (alive) setLists({ Default: [] }); });
    return () => { alive = false; };
  }, [apply]);

  const select = (name: string) => { setActive(name); setShowDetail(true); };

  const submitName = async () => {
    if (!nameDialog) return;
    const trimmed = nameDialog.value.trim();
    if (!trimmed) return;
    setNameDialog(null);
    if (nameDialog.mode === 'new') {
      setLists((prev) => ({ ...(prev ?? {}), [trimmed]: prev?.[trimmed] ?? [] }));
      select(trimmed);
      return;
    }
    if (trimmed === active) return;
    try {
      await axios.put(`${API_BASE}/api/watchlist/${encodeURIComponent(active)}`, { new_name: trimmed });
      setActive(trimmed);
      void reload();
    } catch (e) {
      notify.error(t('renameFailed', { detail: errorDetail(e) }));
    }
  };

  const add = async (s: { symbol: string, name: string }) => {
    try {
      await axios.post(`${API_BASE}/api/watchlist`, { symbol: s.symbol, name: s.name, list_name: active });
      notify.success(t('added', { symbol: s.symbol, list: active }));
      await reload();
    } catch (e) {
      notify.error(t('addFailed', { symbol: s.symbol, detail: errorDetail(e) }));
    }
  };

  const remove = async (symbol: string) => {
    const ok = await confirm({ title: t('removeTitle', { symbol }), body: t('removeBody', { symbol, list: active }), confirmLabel: tc('delete') });
    if (!ok) return;
    try {
      await axios.delete(`${API_BASE}/api/watchlist/${encodeURIComponent(active)}/${encodeURIComponent(symbol)}`);
      notify.success(t('removed', { symbol }));
      void reload();
    } catch (e) {
      notify.error(t('removeFailed', { symbol, detail: errorDetail(e) }));
    }
  };

  if (!lists) {
    return <div className="grid h-full place-items-center text-muted"><Spinner /></div>;
  }
  const items = lists[active] ?? [];
  return (
    <div className="grid h-full min-h-0 lg:grid-cols-[20rem_minmax(0,1fr)]">
      <div className={`min-h-0 ${showDetail ? 'hidden lg:flex' : 'flex'} flex-col`}>
        <ListsPanel lists={lists} active={active} onSelect={select} onNew={() => setNameDialog({ mode: 'new', value: '' })} />
      </div>
      <div className={`min-h-0 ${showDetail ? 'flex' : 'hidden lg:flex'} flex-col`}>
        <ListDetail name={active} items={items} onBack={() => setShowDetail(false)}
          onRename={() => {
            if (PINNED.includes(active)) { notify.warning(t('cannotRename')); return; }
            setNameDialog({ mode: 'rename', value: active });
          }}
          onAddOpen={() => setAdding(true)} onRemove={(s) => void remove(s)} />
      </div>

      <AddSymbolsDrawer open={adding} onOpenChange={setAdding} list={active}
        members={new Set(items.map((s) => s.symbol))} onAdd={add} />

      <Modal.Backdrop isOpen={nameDialog !== null} onOpenChange={(open) => { if (!open) setNameDialog(null); }}>
        <Modal.Container>
          <Modal.Dialog className="sm:max-w-[420px]">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon className="bg-accent-soft text-accent-soft-foreground">
                {nameDialog?.mode === 'rename' ? <Pencil className="size-5" /> : <ListPlus className="size-5" />}
              </Modal.Icon>
              <Modal.Heading>{nameDialog?.mode === 'rename' ? t('renameTitle', { name: active }) : t('newTitle')}</Modal.Heading>
            </Modal.Header>
            <Modal.Body className="space-y-3">
              <form id="watchlist-name" onSubmit={(e) => { e.preventDefault(); void submitName(); }}>
                <TextField autoFocus fullWidth value={nameDialog?.value ?? ''}
                  onChange={(v) => setNameDialog((d) => (d ? { ...d, value: v } : d))}>
                  <Label>{nameDialog?.mode === 'rename' ? t('renameLabel') : t('newLabel')}</Label>
                  <Input placeholder="TOPIC-1028" />
                </TextField>
              </form>
              {nameDialog?.mode === 'new' ? <p className="text-xs text-muted">{t('newHint')}</p> : null}
              {nameDialog?.value.trim() ? (
                <div className="flex items-center gap-3 rounded-xl bg-surface-secondary p-3">
                  <ListAvatar name={nameDialog.value.trim()} />
                  <span className="truncate text-sm font-medium">{splitListName(nameDialog.value.trim()).base}</span>
                </div>
              ) : null}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="tertiary" slot="close">{tc('cancel')}</Button>
              <Button type="submit" form="watchlist-name" isDisabled={!nameDialog?.value.trim()}>
                {nameDialog?.mode === 'rename' ? t('renameConfirm') : t('newConfirm')}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </div>
  );
}
