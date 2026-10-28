import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { FormDialog } from '../../../components/ui/FormDialog.tsx'
import { RenameDialog } from '../../../components/ui/RenameDialog.tsx'
import { fieldClass, fieldErrorClass, formGridClass, inputClass } from
  '../../../components/ui/form.ts'
import { PlusIcon, TrashIcon } from '../../../components/ui/icons.tsx'
import { addItemAction, removeItemAction, renameListAction } from '../api.ts'
import { parseAddItem } from '../model.ts'
import type { Watchlists } from '../schemas.ts'

/** "Add symbol" dialog; the list field suggests existing lists and defaults to the one shown. */
export function AddItemDialog({ lists, list, defaultOpen }: {
  lists: Watchlists
  list: string | null
  defaultOpen?: boolean
}) {
  const add = useAction(addItemAction)
  const empty = { list: list ?? '', symbol: '', name: '', exchange: '' }
  const [form, setForm] = useState(empty)
  const [invalid, setInvalid] = useState<string | null>(null)
  const labels = { list: m.field_list(), symbol: m.field_symbol(), name: m.field_name(),
    exchange: m.field_exchange() }
  return (
    <>
      <FormDialog
        triggerLabel={m.wl_add_title()}
        icon={PlusIcon}
        title={m.wl_add_title()}
        description={m.wl_add_description()}
        submitLabel={m.action_add()}
        pending={add.isPending}
        defaultOpen={defaultOpen}
        testId="wl-add"
        onSubmit={(close) => {
          const parsed = parseAddItem(form)
          setInvalid(parsed.ok ? null : parsed.field)
          if (parsed.ok) {
            add.mutate(parsed.value, { onSuccess: () => {
              setForm({ ...empty, list: form.list })
              close()
            } })
          }
        }}
      >
        <div className={formGridClass}>
          {(Object.keys(labels) as (keyof typeof form)[]).map((key) => (
            <label key={key} className={fieldClass}>
              {labels[key]}
              <input
                className={inputClass}
                value={form[key]}
                list={key === 'list' ? 'wl-names' : undefined}
                aria-invalid={invalid === key}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </label>
          ))}
        </div>
        <datalist id="wl-names">
          {Object.keys(lists).map((n) => <option key={n} value={n} />)}
        </datalist>
        {invalid && (
          <p role="alert" className={fieldErrorClass}>
            {m.invalid_input({ field: labels[invalid as keyof typeof labels] ?? invalid })}
          </p>
        )}
      </FormDialog>
      <ActionStatus action={add} />
    </>
  )
}

export function RenameListDialog({ list }: { list: string }) {
  const rename = useAction(renameListAction)
  return (
    <>
      <RenameDialog
        current={list}
        title={m.wl_rename_title()}
        description={m.wl_rename_description({ list })}
        pending={rename.isPending}
        onRename={(next, close) => rename.mutate({ list, next }, { onSuccess: close })}
      />
      <ActionStatus action={rename} />
    </>
  )
}

/** Row action: remove one symbol from one list, after a confirm naming both. */
export function RemoveItemButton({ list, symbol, defaultOpen }: {
  list: string
  symbol: string
  defaultOpen?: boolean
}) {
  const remove = useAction(removeItemAction)
  return (
    <span className="inline-flex items-center gap-2">
      <ConfirmAction
        iconOnly
        icon={TrashIcon}
        label={m.wl_remove_confirm({ symbol })}
        title={m.wl_remove_title()}
        details={m.wl_remove_details({ symbol, list })}
        confirmLabel={m.wl_remove_confirm({ symbol })}
        disabled={remove.isPending}
        defaultOpen={defaultOpen}
        onConfirm={() => remove.mutate({ list, symbol })}
      />
      <ActionStatus action={remove} />
    </span>
  )
}
