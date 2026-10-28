import { useState } from 'react'
import { m } from '../../paraglide/messages.js'
import { useSymbols, useWatchlist } from '../../services/api/lists.ts'
import { filterSymbols, listSymbols, toggle } from '../../utils/symbols.ts'
import { Chip } from './ChoiceChips.tsx'
import { Badge } from './Feedback.tsx'
import { button, fieldClass, formRowClass, inputClass, selectClass } from './form.ts'

const VISIBLE = 200

/** Multi-select over /api/symbols, with "pick a whole watchlist" and a text filter. */
export function SymbolPicker({ value, onChange }: {
  value: string[]
  onChange: (next: string[]) => void
}) {
  const symbols = useSymbols().data?.symbols ?? []
  const lists = useWatchlist().data ?? {}
  const [query, setQuery] = useState('')
  const shown = filterSymbols(symbols, query, VISIBLE)
  return (
    <fieldset className="space-y-3 rounded-lg border p-4" data-testid="symbol-picker">
      <legend className="px-1 text-sm font-medium">
        <Badge tone={value.length > 0 ? 'default' : 'secondary'}>
          {m.field_symbols_picked({ count: value.length })}
        </Badge>
      </legend>
      <div className={formRowClass}>
        <label className={fieldClass}>
          {m.picker_filter()}
          <input className={inputClass} type="search" value={query}
            onChange={(e) => setQuery(e.target.value)} />
        </label>
        <label className={fieldClass}>
          {m.picker_from_list()}
          <select className={selectClass} value=""
            onChange={(e) => e.target.value && onChange(listSymbols(lists, e.target.value))}>
            <option value="">—</option>
            {Object.keys(lists).sort().map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </label>
        <button type="button" className={button('outline', 'sm')}
          onClick={() => onChange([...new Set([...value, ...shown.map((s) => s.symbol)])])}>
          {m.action_select_all()}
        </button>
        <button type="button" className={button('ghost', 'sm')} onClick={() => onChange([])}>
          {m.action_clear_selection()}
        </button>
      </div>
      <div className="flex max-h-40 flex-wrap gap-1.5 overflow-auto">
        {shown.map((s) => (
          <Chip key={s.symbol} title={s.name ?? ''} checked={value.includes(s.symbol)}
            onChange={(on) => onChange(toggle(value, s.symbol, on))}>
            {s.symbol}
          </Chip>
        ))}
      </div>
    </fieldset>
  )
}
