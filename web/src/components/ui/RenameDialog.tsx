import { useState } from 'react'
import { m } from '../../paraglide/messages.js'
import { FormDialog } from './FormDialog.tsx'
import { fieldClass, inputClass } from './form.ts'
import { PencilIcon } from './icons.tsx'

/** "Rename" button + modal with one name field. An empty or unchanged name just closes;
 * `onRename` gets the trimmed name and `close` for when the server accepted it. */
export function RenameDialog({ current, title, description, pending, onRename }: {
  current: string
  title: string
  description: string
  pending: boolean
  onRename: (next: string, close: () => void) => void
}) {
  const [next, setNext] = useState(current)
  return (
    <FormDialog
      triggerLabel={title}
      icon={PencilIcon}
      variant="outline"
      size="sm"
      title={title}
      description={description}
      submitLabel={m.action_rename()}
      pending={pending}
      onSubmit={(close) => {
        const name = next.trim()
        if (!name || name === current) close()
        else onRename(name, close)
      }}
    >
      <label className={fieldClass}>
        {m.field_new_name()}
        <input className={inputClass} value={next} onChange={(e) => setNext(e.target.value)} />
      </label>
    </FormDialog>
  )
}
