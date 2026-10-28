import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { domainConfig } from '../../../config/domain.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../../components/ui/ConfirmAction.tsx'
import { Badge, type Tone } from '../../../components/ui/Feedback.tsx'
import { button, fieldClass, formRowClass, hintClass, inputClass, selectClass } from
  '../../../components/ui/form.ts'
import { RadarIcon } from '../../../components/ui/icons.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { saveTvModeAction, saveTvTokenAction, tvModeQuery, tvTokenQuery } from '../api.ts'
import type { TvTokenStatus } from '../schemas.ts'

const modeLabel = (mode: number) =>
  mode === 1 ? m.tv_mode_1() : mode === 2 ? m.tv_mode_2() : m.tv_mode_3()

export function tokenStatusText(s: TvTokenStatus): string {
  if (s.status === 'active') return m.tv_token_active({ minutes: s.expires_in_minutes ?? 0 })
  if (s.status === 'expired') return m.tv_token_expired()
  return m.tv_token_none()
}

const tokenTone = (s: TvTokenStatus): Tone =>
  s.status === 'active' ? 'success' : s.status === 'expired' ? 'destructive' : 'secondary'

/** Changing the mode drops the server's cached login, so the new value is confirmed first;
 * the select keeps showing the saved mode until then. */
export function TvModeSelect({ mode, defaultAsk = null }: {
  mode: number
  defaultAsk?: number | null
}) {
  const save = useAction(saveTvModeAction)
  const [ask, setAsk] = useState<number | null>(defaultAsk)
  return (
    <div className="space-y-1.5">
      <label className={fieldClass}>
        {m.tv_mode_label()}
        <select className={`${selectClass} max-w-xs`} value={mode} disabled={save.isPending}
          onChange={(e) => setAsk(Number(e.target.value))}>
          {domainConfig.domain.tvModes.map((v) => (
            <option key={v} value={v}>{modeLabel(v)}</option>
          ))}
        </select>
      </label>
      <p className={hintClass}>{m.tv_mode_hint()}</p>
      <ConfirmDialog
        open={ask !== null}
        tone="danger"
        title={m.tv_mode_confirm_title()}
        details={ask !== null && m.tv_mode_confirm({ mode: modeLabel(ask) })}
        confirmLabel={m.tv_mode_confirm_button()}
        onCancel={() => setAsk(null)}
        onConfirm={() => {
          if (ask !== null) save.mutate(ask)
          setAsk(null)
        }}
      />
      <ActionStatus action={save} />
    </div>
  )
}

function TvTokenForm() {
  const save = useAction(saveTvTokenAction, { success: tokenStatusText })
  const [token, setToken] = useState('')
  return (
    <form className={formRowClass} onSubmit={(e) => {
      e.preventDefault()
      if (token.trim()) save.mutate(token.trim(), { onSuccess: () => setToken('') })
    }}>
      <label className={fieldClass}>
        {m.tv_token_input()}
        <input className={`${inputClass} w-72 max-w-full`} type="password" autoComplete="off"
          spellCheck={false} value={token} onChange={(e) => setToken(e.target.value)} />
      </label>
      <button type="submit" className={button('default')}
        disabled={!token.trim() || save.isPending}>
        {m.action_save()}
      </button>
      <ActionStatus action={save} />
    </form>
  )
}

export function TvSettings() {
  const modeQ = useQuery(tvModeQuery)
  const tokenQ = useQuery(tvTokenQuery)
  return (
    <Card>
      <CardHeader icon={RadarIcon} title={m.settings_tv()} description={m.settings_tv_hint()}
        actions={(
          <QueryState query={tokenQ}>
            {(d) => <Badge tone={tokenTone(d)} testId="tv-token-status">
              {tokenStatusText(d)}</Badge>}
          </QueryState>
        )} />
      <CardContent className="space-y-6">
        <QueryState query={modeQ}>{(d) => <TvModeSelect mode={d.mode} />}</QueryState>
        <TvTokenForm />
      </CardContent>
    </Card>
  )
}
