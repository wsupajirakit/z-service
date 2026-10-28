import {
  Avatar, Button, FieldError, Input, Label, Modal, Popover, Separator, TextField,
} from '@heroui/react';
import axios from 'axios';
import { Check, Eye, EyeOff, KeyRound, LogOut, ShieldCheck, X } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { currentAccount, signOut, storeToken } from '../auth';
import { API_BASE } from '../core';
import { useT } from '../i18n';
import { account } from '../i18n/messages/account';
import { common } from '../i18n/messages/common';
import { useConfirm } from './confirmContext';
import { errorDetail, notify } from './notify';
import { LanguageSwitch, ThemeSwitch } from './Preferences';

const MIN_PASSWORD = 12; // the server's rule (backend auth routes: MIN_PASSWORD_LEN)

function initials(name: string) {
  const parts = name.trim().split(/[\s._@-]+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
  return letters.toUpperCase() || '?';
}

function Rule({ ok, children }: { ok: boolean, children: ReactNode }) {
  return (
    <li className={`flex items-center gap-2 text-xs ${ok ? 'text-success' : 'text-muted'}`}>
      <span className={`grid size-4 place-items-center rounded-full ${ok ? 'bg-success-soft' : 'bg-surface-secondary'}`}>
        {ok ? <Check className="size-3" /> : <X className="size-3" />}
      </span>
      {children}
    </li>
  );
}

type Problem = 'wrongCurrent' | 'tooShort' | 'unchanged' | 'tooMany' | null;

function ChangePasswordDialog({ open, onOpenChange }: { open: boolean, onOpenChange: (open: boolean) => void }) {
  const t = useT(account);
  const tc = useT(common);
  const [form, setForm] = useState({ current: '', next: '', repeat: '' });
  const [shown, setShown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<Problem>(null);
  const long = form.next.length >= MIN_PASSWORD;
  const match = form.next !== '' && form.next === form.repeat;
  const differs = form.next !== '' && form.next !== form.current;
  const ready = form.current !== '' && long && match && differs;

  const close = (next: boolean) => {
    if (!next) { setForm({ current: '', next: '', repeat: '' }); setProblem(null); setShown(false); }
    onOpenChange(next);
  };

  const save = async () => {
    if (!ready) return;
    setSaving(true);
    setProblem(null);
    try {
      const res = await axios.post<{ token: string }>(`${API_BASE}/api/auth/password`, {
        current_password: form.current, new_password: form.next,
      });
      storeToken(res.data.token);
      notify.success(t('saved'));
      close(false);
    } catch (err) {
      const code = (err as { response?: { status?: number, data?: { code?: string } } }).response;
      if (code?.data?.code === 'auth.wrong_current_password') setProblem('wrongCurrent');
      else if (code?.data?.code === 'auth.password_short') setProblem('tooShort');
      else if (code?.data?.code === 'auth.password_unchanged') setProblem('unchanged');
      else if (code?.status === 429) setProblem('tooMany');
      else notify.error(t('failed', { detail: errorDetail(err) }));
    } finally {
      setSaving(false);
    }
  };

  const field = (key: 'current' | 'next' | 'repeat', autoComplete: string, invalid?: string) => (
    <TextField isInvalid={Boolean(invalid)} className="w-full" type={shown ? 'text' : 'password'}
      value={form[key]} onChange={(value) => { setForm({ ...form, [key]: value }); setProblem(null); }}>
      <Label>{t(key)}</Label>
      <Input autoComplete={autoComplete} />
      {invalid ? <FieldError>{invalid}</FieldError> : null}
    </TextField>
  );
  const message = problem === 'wrongCurrent' ? t('wrongCurrent') : problem === 'tooShort'
    ? t('tooShort', { n: MIN_PASSWORD }) : problem === 'unchanged' ? t('unchanged')
      : problem === 'tooMany' ? t('tooMany') : undefined;

  return (
    <Modal.Backdrop isOpen={open} onOpenChange={close}>
      <Modal.Container>
        <Modal.Dialog className="sm:max-w-[440px]">
          <Modal.CloseTrigger />
          <Modal.Header>
            <Modal.Icon className="bg-accent-soft text-accent-soft-foreground"><KeyRound className="size-5" /></Modal.Icon>
            <Modal.Heading>{t('changePassword')}</Modal.Heading>
          </Modal.Header>
          <Modal.Body>
            <form id="change-password" className="space-y-4" onSubmit={(e) => { e.preventDefault(); void save(); }}>
              {field('current', 'current-password', problem === 'wrongCurrent' || problem === 'tooMany' ? message : undefined)}
              {field('next', 'new-password', problem === 'tooShort' || problem === 'unchanged' ? message : undefined)}
              {field('repeat', 'new-password')}
              <ul className="space-y-1.5 rounded-xl bg-surface-secondary p-3">
                <Rule ok={long}>{t('ruleLength', { n: MIN_PASSWORD })}</Rule>
                <Rule ok={match}>{t('ruleMatch')}</Rule>
                <Rule ok={differs}>{t('ruleDiffers')}</Rule>
              </ul>
              <Button size="sm" variant="ghost" onPress={() => setShown(!shown)}>
                {shown ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                {shown ? t('hide') : t('show')}
              </Button>
              <p className="text-xs text-muted">{t('changePasswordHint')}</p>
            </form>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="tertiary" slot="close">{tc('cancel')}</Button>
            <Button type="submit" form="change-password" isDisabled={!ready} isPending={saving}>
              {saving ? tc('saving') : tc('save')}
            </Button>
          </Modal.Footer>
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}

function sessionLeft(expiresAt: number | null, t: ReturnType<typeof useT<keyof typeof account.en>>) {
  if (!expiresAt) return '';
  const minutes = Math.max(0, Math.round((expiresAt - Date.now()) / 60000));
  return t('sessionEnds', { time: minutes >= 60 ? t('hours', { n: Math.floor(minutes / 60) }) : t('minutes', { n: minutes }) });
}

/** The avatar in the header: who is signed in, preferences, password change and sign-out. */
export function AccountMenu() {
  const t = useT(account);
  const confirm = useConfirm();
  const [panelOpen, setPanelOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const me = currentAccount();
  const name = me?.username || '—';

  const askSignOut = async () => {
    setPanelOpen(false);
    if (!(await confirm({ title: t('signOutTitle'), body: t('signOutBody'), confirmLabel: t('signOut') }))) return;
    setSigningOut(true);
    await signOut();
  };

  return (
    <>
      <Popover isOpen={panelOpen} onOpenChange={setPanelOpen}>
        <Button isIconOnly variant="ghost" aria-label={t('open')} className="rounded-full p-0" isPending={signingOut}>
          <span className="relative">
            <Avatar size="sm" className="ring-2 ring-accent/40">
              <Avatar.Fallback className="bg-accent text-accent-foreground text-xs font-semibold">{initials(name)}</Avatar.Fallback>
            </Avatar>
            <span className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full bg-success ring-2 ring-background" />
          </span>
        </Button>
        <Popover.Content placement="bottom end" className="w-80 p-0">
          <Popover.Dialog className="p-0">
            <div className="flex items-center gap-3 p-4">
              <Avatar size="lg">
                <Avatar.Fallback className="bg-accent text-accent-foreground font-semibold">{initials(name)}</Avatar.Fallback>
              </Avatar>
              <div className="min-w-0">
                <div className="text-xs text-muted">{t('signedInAs')}</div>
                <div className="truncate font-semibold">{name}</div>
                <div className="flex items-center gap-1 text-xs text-muted">
                  <ShieldCheck className="size-3.5 text-success" />{sessionLeft(me?.expiresAt ?? null, t)}
                </div>
              </div>
            </div>
            <Separator />
            <div className="space-y-3 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-muted">{t('preferences')}</div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span>{t('language')}</span><LanguageSwitch />
              </div>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span>{t('theme')}</span><ThemeSwitch />
              </div>
            </div>
            <Separator />
            <div className="space-y-1 p-2">
              <div className="px-2 pt-2 text-xs font-medium uppercase tracking-wide text-muted">{t('security')}</div>
              <Button variant="ghost" fullWidth onPress={() => { setPanelOpen(false); setPasswordOpen(true); }}
                className="h-auto justify-start gap-3 rounded-xl px-2 py-2 text-left">
                <span className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent-soft-foreground"><KeyRound className="size-4" /></span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium">{t('changePassword')}</span>
                  <span className="block text-xs text-muted">{t('changePasswordHint')}</span>
                </span>
              </Button>
              <Button variant="ghost" fullWidth onPress={() => void askSignOut()}
                className="h-auto justify-start gap-3 rounded-xl px-2 py-2 text-left hover:bg-danger-soft">
                <span className="grid size-8 place-items-center rounded-lg bg-danger-soft text-danger"><LogOut className="size-4" /></span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-danger">{t('signOut')}</span>
                  <span className="block text-xs text-muted">{t('signOutHint')}</span>
                </span>
              </Button>
            </div>
          </Popover.Dialog>
        </Popover.Content>
      </Popover>
      <ChangePasswordDialog open={passwordOpen} onOpenChange={setPasswordOpen} />
    </>
  );
}
