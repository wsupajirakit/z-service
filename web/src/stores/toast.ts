// Toast queue: write actions report their result here and the shell's <Toaster> shows it.
// Plain module state (no React Context), the same pattern as the locale and theme stores.
export type ToastTone = 'success' | 'error' | 'info'
export type Toast = { id: number; tone: ToastTone; text: string }

/** How long a toast stays (ms); errors stay longer so they can be read. */
export const TOAST_MS: Record<ToastTone, number> = { success: 4000, info: 4000, error: 8000 }
/** Older toasts drop off once this many are on screen. */
export const TOAST_LIMIT = 4

let toasts: readonly Toast[] = []
let nextId = 1
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((fn) => fn())

export function getToasts(): readonly Toast[] {
  return toasts
}

export function dismissToast(id: number): void {
  if (!toasts.some((t) => t.id === id)) return
  toasts = toasts.filter((t) => t.id !== id)
  emit()
}

/** Shows a toast and schedules its removal; returns its id. */
export function showToast(tone: ToastTone, text: string): number {
  const id = nextId++
  toasts = [...toasts, { id, tone, text }].slice(-TOAST_LIMIT)
  emit()
  setTimeout(() => dismissToast(id), TOAST_MS[tone])
  return id
}

export function clearToasts(): void {
  toasts = []
  emit()
}

export function subscribeToasts(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
