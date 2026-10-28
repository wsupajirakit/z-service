import { useSyncExternalStore } from 'react'
import { currentLocale, subscribeLocale } from '../stores/locale.ts'

export function useLocale() {
  return useSyncExternalStore(subscribeLocale, currentLocale, currentLocale)
}
