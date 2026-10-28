import { m } from '../../paraglide/messages.js'
import { toggleTheme } from '../../stores/theme.ts'
import { useTheme } from '../../hooks/useTheme.ts'
import { button } from './form.ts'
import { MoonIcon, SunIcon } from './icons.tsx'

/** Sun in dark mode (click for light), moon in light mode (click for dark). */
export function ThemeToggle() {
  const theme = useTheme()
  const label = theme === 'dark' ? m.theme_to_light() : m.theme_to_dark()
  return (
    <button type="button" className={button('ghost', 'icon')} onClick={toggleTheme}
      aria-label={label} title={label} data-testid="theme" data-theme-value={theme}>
      {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
    </button>
  )
}
