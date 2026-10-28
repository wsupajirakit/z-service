import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { FormDialog } from '../../../components/ui/FormDialog.tsx'
import { RenameDialog } from '../../../components/ui/RenameDialog.tsx'
import { fieldClass, fieldErrorClass, formGridClass, inputClass, selectClass } from
  '../../../components/ui/form.ts'
import { PlusIcon, TrashIcon } from '../../../components/ui/icons.tsx'
import { addTradeAction, removeSymbolAction, renamePortAction } from '../api.ts'
import { parseTrade, type TradeForm } from '../model.ts'

/** "Add trade" dialog; a new portfolio name creates the portfolio. */
export function AddTradeDialog({ ports, defaultOpen }: { ports: string[]; defaultOpen?: boolean }) {
  const add = useAction(addTradeAction)
  const empty: TradeForm = { port: ports[0] ?? '', symbol: '', quantity: '', price: '',
    action: 'buy' }
  const [form, setForm] = useState(empty)
  const [invalid, setInvalid] = useState<keyof TradeForm | null>(null)
  const labels = { port: m.field_portfolio(), symbol: m.field_symbol(),
    quantity: m.col_quantity(), price: m.col_price() }
  return (
    <>
      <FormDialog
        triggerLabel={m.pf_add_title()}
        icon={PlusIcon}
        title={m.pf_add_title()}
        description={m.pf_add_description()}
        submitLabel={m.action_add()}
        pending={add.isPending}
        defaultOpen={defaultOpen}
        testId="pf-add"
        onSubmit={(close) => {
          const parsed = parseTrade(form)
          setInvalid(parsed.ok ? null : parsed.field)
          if (!parsed.ok) return
          add.mutate(parsed.value, { onSuccess: () => {
            setForm({ ...empty, port: form.port })
            close()
          } })
        }}
      >
        <div className={formGridClass}>
          {(Object.keys(labels) as (keyof typeof labels)[]).map((key) => (
            <label key={key} className={fieldClass}>
              {labels[key]}
              <input
                className={inputClass}
                value={form[key]}
                list={key === 'port' ? 'pf-names' : undefined}
                inputMode={key === 'quantity' || key === 'price' ? 'decimal' : undefined}
                aria-invalid={invalid === key}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </label>
          ))}
          <label className={fieldClass}>
            {m.col_action()}
            <select className={selectClass} value={form.action}
              onChange={(e) => setForm({ ...form,
                action: e.target.value === 'sell' ? 'sell' : 'buy' })}>
              <option value="buy">{m.trade_buy()}</option>
              <option value="sell">{m.trade_sell()}</option>
            </select>
          </label>
        </div>
        <datalist id="pf-names">{ports.map((p) => <option key={p} value={p} />)}</datalist>
        {invalid && invalid !== 'action' && (
          <p role="alert" className={fieldErrorClass}>
            {m.invalid_input({ field: labels[invalid] })}
          </p>
        )}
      </FormDialog>
      <ActionStatus action={add} />
    </>
  )
}

export function RenamePortDialog({ port }: { port: string }) {
  const rename = useAction(renamePortAction)
  return (
    <>
      <RenameDialog
        current={port}
        title={m.pf_rename_title()}
        description={m.pf_rename_description({ port })}
        pending={rename.isPending}
        onRename={(next, close) => rename.mutate({ port, next }, { onSuccess: close })}
      />
      <ActionStatus action={rename} />
    </>
  )
}

/** Row action: delete every trade of one symbol in one portfolio, after a confirm. */
export function RemoveSymbolButton({ port, symbol, defaultOpen }: {
  port: string
  symbol: string
  defaultOpen?: boolean
}) {
  const remove = useAction(removeSymbolAction)
  return (
    <span className="inline-flex items-center gap-2">
      <ConfirmAction
        iconOnly
        icon={TrashIcon}
        label={m.pf_remove_confirm({ symbol })}
        title={m.pf_remove_title()}
        details={m.pf_remove_details({ symbol, port })}
        confirmLabel={m.pf_remove_confirm({ symbol })}
        disabled={remove.isPending}
        defaultOpen={defaultOpen}
        onConfirm={() => remove.mutate({ port, symbol })}
      />
      <ActionStatus action={remove} />
    </span>
  )
}
