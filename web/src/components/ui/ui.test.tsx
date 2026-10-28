import { afterEach, describe, expect, it } from 'vitest'
import { m } from '../../paraglide/messages.js'
import { renderPage } from '../../testing/mocks/renderPage.tsx'
import { clearToasts, showToast } from '../../stores/toast.ts'
import { ConfirmAction } from './ConfirmAction.tsx'
import { DataTable, type Column } from './DataTable.tsx'
import { FormDialog } from './FormDialog.tsx'
import { LocaleToggle } from './LocaleToggle.tsx'
import { Tabs } from './Tabs.tsx'
import { ThemeToggle } from './ThemeToggle.tsx'
import { Toaster } from './Toaster.tsx'

type Row = { sym: string; n: number }
const rows: Row[] = Array.from({ length: 30 }, (_, i) => ({ sym: `S${i + 1}`, n: 30 - i }))
const columns: Column<Row>[] = [
  { id: 'sym', header: 'Sym', value: (r) => r.sym },
  { id: 'n', header: 'N', numeric: true, value: (r) => r.n },
  { id: 'act', header: '' },
]

describe('shared ui', () => {
  afterEach(() => clearToasts())

  it('table: search box, sortable headers, first page and its range', () => {
    const html = renderPage(<DataTable rows={rows} columns={columns} rowKey={(r) => r.sym}
      testId="t" initialSort={{ id: 'n', desc: false }} />, [])
    expect(html).toContain('data-testid="table-search"')
    expect(html.match(/<th[^>]*><button/g)).toHaveLength(2)
    expect(html).toContain('aria-sort="ascending"')
    expect(html).toContain(m.table_range({ from: 1, to: 25, total: 30 }))
    expect(html.match(/data-row="/g)).toHaveLength(25)
    // Ascending by N: S30 (n = 1) first, S6 (n = 25) last on page one.
    expect(html.indexOf('>S30<')).toBeLessThan(html.indexOf('>S6<'))
    expect(html).not.toContain('>S5<')
  })

  it('table: an empty list shows the empty state, not a blank grid', () => {
    const html = renderPage(<DataTable rows={[]} columns={columns} rowKey={(r) => r.sym} />, [])
    expect(html).toContain('data-testid="empty-state"')
    expect(html).toContain(m.table_range({ from: 0, to: 0, total: 0 }))
  })

  it('confirm: closed shows only the trigger; open is a themed alert dialog', () => {
    const props = { label: 'L', title: 'T', details: 'D', confirmLabel: 'C', onConfirm: () => {} }
    expect(renderPage(<ConfirmAction {...props} />, [])).not.toContain('confirm-panel')
    const open = renderPage(<ConfirmAction {...props} tone="cost" defaultOpen />, [])
    expect(open).toContain('role="alertdialog"')
    expect(open).toContain('data-testid="confirm-panel"')
    expect(open).toContain('data-testid="cost-warning"')
    expect(open).toContain(m.confirm_cancel())
  })

  it('form dialog: the body and footer are one form with cancel and submit', () => {
    const text = { triggerLabel: 'Add', title: 'New', submitLabel: 'Save' }
    const html = renderPage(<FormDialog {...text} onSubmit={() => {}} defaultOpen testId="fd">
      <input name="x" />
    </FormDialog>, [])
    expect(html).toMatch(/<form[^>]*novalidate/i)
    expect(html).toContain('name="x"')
    expect(html).toContain('type="submit"')
    expect(html).toContain(m.dialog_close())
  })

  it('toaster renders queued toasts with a role per tone', () => {
    showToast('success', 'Saved it')
    showToast('error', 'Broke it')
    const html = renderPage(<Toaster />, [])
    expect(html).toContain('Saved it')
    expect(html).toMatch(/role="alert"[^>]*data-tone="error"/)
    expect(html).toMatch(/role="status"[^>]*data-tone="success"/)
  })

  it('header toggles: dark by default offers light; language button shows the code', () => {
    const theme = renderPage(<ThemeToggle />, [])
    expect(theme).toContain('data-theme-value="dark"')
    expect(theme).toContain(`aria-label="${m.theme_to_light()}"`)
    const locale = renderPage(<LocaleToggle />, [])
    expect(locale).toContain('aria-haspopup="menu"')
    expect(locale).toContain('>en<')
  })

  it('tabs mark the selected tab and link tabs to panels when given an id base', () => {
    const items = [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]
    const html = renderPage(<Tabs label={m.nav_label()} value="b" onChange={() => {}}
      idBase="s" items={items} />, [])
    expect(html).toContain('role="tablist"')
    expect(html).toMatch(/id="s-tab-b" aria-controls="s-panel-b" aria-selected="true"/)
    expect(html.match(/aria-selected="false"/g)).toHaveLength(1)
  })
})
