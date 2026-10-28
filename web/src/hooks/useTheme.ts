import { useSyncExternalStore } from 'react'
import { getTheme, subscribeTheme } from '../stores/theme.ts'

/** Server renders (tests) see the default theme. */
export function useTheme() {
  return useSyncExternalStore(subscribeTheme, getTheme, () => 'dark' as const)
}
