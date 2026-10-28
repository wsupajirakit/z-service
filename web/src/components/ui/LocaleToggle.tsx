import { m } from '../../paraglide/messages.js'
import type { Locale } from '../../paraglide/runtime.js'
import { LOCALES, changeLocale } from '../../stores/locale.ts'
import { useLocale } from '../../hooks/useLocale.ts'
import { LanguagesIcon } from './icons.tsx'
import { Menu } from './Menu.tsx'

/** Each language named in itself (from Intl, not a hand-written list). */
function languageName(locale: Locale): string {
  return new Intl.DisplayNames([locale], { type: 'language' }).of(locale) ?? locale
}

/** Header button showing the current language code; the menu lists every locale. */
export function LocaleToggle() {
  const locale = useLocale()
  return (
    <Menu
      testId="locale"
      label={m.locale_label()}
      trigger={(
        <>
          <LanguagesIcon />
          <span className="font-semibold uppercase">{locale}</span>
        </>
      )}
      items={LOCALES.map((l) => ({
        key: l,
        label: languageName(l),
        checked: l === locale,
        icon: <span className="w-6 text-xs font-semibold text-muted-foreground uppercase">
          {l}</span>,
        onSelect: () => changeLocale(l),
      }))}
    />
  )
}
