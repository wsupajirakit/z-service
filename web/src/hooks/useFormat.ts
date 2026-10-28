import { useTimezone } from '../services/api/common.ts'
import { cellText, formatDateTime, formatNumber } from '../utils/format.ts'
import { useLocale } from './useLocale.ts'

/** Formatters bound to the selected locale and the server display timezone. */
export function useFormat() {
  const locale = useLocale()
  const zone = useTimezone()
  return {
    locale,
    dateTime: (value: string | null | undefined) => formatDateTime(value, locale, zone),
    number: (value: unknown, digits?: number) => formatNumber(value, locale, digits),
    cell: (value: unknown) => cellText(value, locale),
  }
}
