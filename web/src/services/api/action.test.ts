import { afterEach, describe, expect, it } from 'vitest'
import { m } from '../../paraglide/messages.js'
import { clearToasts, getToasts } from '../../stores/toast.ts'
import { notifyError, notifySuccess } from './action.ts'
import { ApiError } from './error.ts'

const shown = () => getToasts().map(({ tone, text }) => ({ tone, text }))

describe('action results become toasts', () => {
  afterEach(() => clearToasts())

  it('success uses the page text, else "done"', () => {
    notifySuccess({}, { status: 'ok' })
    notifySuccess({ success: (d: { n: number }) => `saved ${d.n}` }, { n: 3 })
    expect(shown()).toEqual([
      { tone: 'success', text: m.action_done() },
      { tone: 'success', text: 'saved 3' },
    ])
  })

  it('errors are translated by code; silent actions show nothing', () => {
    notifyError({}, new ApiError(500, 'plain'))
    notifyError({ silent: true }, new ApiError(500, 'plain'))
    notifySuccess({ silent: true }, 1)
    expect(shown()).toEqual([
      { tone: 'error', text: m.error_http({ status: 500, detail: 'plain' }) },
    ])
  })
})
