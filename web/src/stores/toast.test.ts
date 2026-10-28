import { afterEach, describe, expect, it, vi } from 'vitest'
import { TOAST_LIMIT, TOAST_MS, clearToasts, dismissToast, getToasts, showToast,
  subscribeToasts } from './toast.ts'

describe('toast store', () => {
  afterEach(() => {
    clearToasts()
    vi.useRealTimers()
  })

  it('shows, notifies and dismisses a toast', () => {
    const seen: number[] = []
    const stop = subscribeToasts(() => seen.push(getToasts().length))
    const id = showToast('success', 'Saved')
    expect(getToasts()).toEqual([{ id, tone: 'success', text: 'Saved' }])
    dismissToast(id)
    dismissToast(id)
    stop()
    expect(getToasts()).toEqual([])
    expect(seen).toEqual([1, 0])
  })

  it('removes each toast after its tone time; errors stay longer', () => {
    vi.useFakeTimers()
    showToast('success', 'ok')
    showToast('error', 'failed')
    vi.advanceTimersByTime(TOAST_MS.success)
    expect(getToasts().map((t) => t.text)).toEqual(['failed'])
    vi.advanceTimersByTime(TOAST_MS.error - TOAST_MS.success)
    expect(getToasts()).toEqual([])
  })

  it('keeps only the newest toasts on screen', () => {
    for (let i = 0; i < TOAST_LIMIT + 2; i++) showToast('info', `t${i}`)
    expect(getToasts().map((t) => t.text)).toEqual(['t2', 't3', 't4', 't5'])
  })
})
