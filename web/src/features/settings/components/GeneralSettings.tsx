import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { domainConfig } from '../../../config/domain.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../../components/ui/ConfirmAction.tsx'
import { button, fieldClass, fieldErrorClass, formRowClass, inputClass } from
  '../../../components/ui/form.ts'
import { HistoryIcon, MailIcon, RefreshIcon } from '../../../components/ui/icons.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { Switch } from '../../../components/ui/Switch.tsx'
import {
  autoSkipQuery, destinationsQuery, saveAutoSkipAction, saveDestinationAction,
  saveTimezoneAction, timezoneQuery,
} from '../api.ts'
import { browserZone, parseAutoSkip, parseTimezone } from '../model.ts'
import { destinationKeys, type DestinationKey, type Destinations,
  type TimezoneSetting } from '../schemas.ts'

const { timezoneOffsetMinutes: tz, autoSkipMinutes: skip } = domainConfig.limits

function TimezoneForm({ current }: { current: TimezoneSetting }) {
  const save = useAction(saveTimezoneAction)
  const [offset, setOffset] = useState(String(current.offset_minutes))
  const [label, setLabel] = useState(current.label)
  const parsed = parseTimezone(offset, label)
  return (
    <form className="space-y-3" data-testid="tz-form" onSubmit={(e) => {
      e.preventDefault()
      if (parsed) save.mutate(parsed)
    }}>
      <div className={formRowClass}>
        <label className={fieldClass}>
          {m.tz_offset({ min: tz.min, max: tz.max })}
          <input className={`${inputClass} w-32`} type="number" min={tz.min} max={tz.max}
            value={offset} onChange={(e) => setOffset(e.target.value)} />
        </label>
        <label className={fieldClass}>
          {m.tz_label()}
          <input className={inputClass} value={label} onChange={(e) => setLabel(e.target.value)} />
        </label>
        <button type="button" className={button('outline')} onClick={() => {
          const z = browserZone()
          setOffset(String(z.offset))
          setLabel(z.label)
        }}>
          {m.tz_use_browser()}
        </button>
        <button type="submit" className={button('default')} disabled={!parsed || save.isPending}>
          {m.action_save()}
        </button>
      </div>
      {!parsed && <p role="alert" className={fieldErrorClass}>{m.tz_invalid()}</p>}
      <ActionStatus action={save} />
    </form>
  )
}

const destLabel = (key: DestinationKey) => ({
  dest_stock_drive: m.dest_stock_drive(),
  dest_stock_telegram: m.dest_stock_telegram(),
  dest_gold_drive: m.dest_gold_drive(),
  dest_gold_telegram: m.dest_gold_telegram(),
})[key]

/** Each switch asks first; it shows the saved value until the change is confirmed. */
export function DestinationToggles({ dest, defaultAsk = null }: {
  dest: Destinations
  /** Tests server-render the confirm step for one switch. */
  defaultAsk?: DestinationKey | null
}) {
  const save = useAction(saveDestinationAction)
  const [ask, setAsk] = useState<DestinationKey | null>(defaultAsk)
  const on = ask ? !dest[ask] : false
  return (
    <div className="divide-y" data-testid="dest-form">
      {destinationKeys.map((key) => (
        <div key={key} className="flex items-center justify-between gap-4 py-3 text-sm">
          <span className="font-medium">{destLabel(key)}</span>
          <Switch checked={dest[key]} label={destLabel(key)} testId={`switch-${key}`}
            disabled={save.isPending} onChange={() => setAsk(key)} />
        </div>
      ))}
      <ConfirmDialog
        open={ask !== null}
        tone={on ? 'normal' : 'danger'}
        title={on ? m.dest_confirm_on_title() : m.dest_confirm_off_title()}
        details={ask && (on ? m.dest_confirm_on({ name: destLabel(ask) })
          : m.dest_confirm_off({ name: destLabel(ask) }))}
        confirmLabel={on ? m.dest_turn_on() : m.dest_turn_off()}
        onCancel={() => setAsk(null)}
        onConfirm={() => {
          if (ask) save.mutate({ key: ask, on })
          setAsk(null)
        }}
      />
      <ActionStatus action={save} />
    </div>
  )
}

function AutoSkipForm({ minutes }: { minutes: number }) {
  const save = useAction(saveAutoSkipAction)
  const [value, setValue] = useState(String(minutes))
  const parsed = parseAutoSkip(value)
  return (
    <form className={formRowClass} onSubmit={(e) => {
      e.preventDefault()
      if (parsed !== null) save.mutate(parsed)
    }}>
      <label className={fieldClass}>
        {m.auto_skip_label({ min: skip.min, max: skip.max })}
        <input className={`${inputClass} w-32`} type="number" min={skip.min} max={skip.max}
          value={value} onChange={(e) => setValue(e.target.value)} />
      </label>
      <button type="submit" className={button('default')}
        disabled={parsed === null || save.isPending}>
        {m.action_save()}
      </button>
      <ActionStatus action={save} />
    </form>
  )
}

export function GeneralSettings() {
  const tzQ = useQuery(timezoneQuery)
  const destQ = useQuery(destinationsQuery)
  const skipQ = useQuery(autoSkipQuery)
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader icon={HistoryIcon} title={m.settings_timezone()}
          description={m.settings_timezone_hint()} />
        <CardContent>
          <QueryState query={tzQ}>{(d) => <TimezoneForm key={d.label} current={d} />}</QueryState>
        </CardContent>
      </Card>
      <Card>
        <CardHeader icon={MailIcon} title={m.settings_destinations()}
          description={m.settings_destinations_hint()} />
        <CardContent>
          <QueryState query={destQ}>{(d) => <DestinationToggles dest={d} />}</QueryState>
        </CardContent>
      </Card>
      <Card>
        <CardHeader icon={RefreshIcon} title={m.settings_auto_skip()}
          description={m.settings_auto_skip_hint()} />
        <CardContent>
          <QueryState query={skipQ}>
            {(d) => <AutoSkipForm key={d.minutes} minutes={d.minutes} />}
          </QueryState>
        </CardContent>
      </Card>
    </div>
  )
}
