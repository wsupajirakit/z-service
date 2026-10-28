import { ToggleButton, ToggleButtonGroup, Tooltip } from '@heroui/react';
import { Monitor, Moon, Sun, type LucideIcon } from 'lucide-react';
import { LANGS, setLang, useLang, useT, type Lang, type MessageKey } from '../i18n';
import { shell } from '../i18n/messages/shell';
import { setThemePref, useTheme, type ThemePref } from '../theme';

type ShellKey = MessageKey<typeof shell>;

export function LanguageSwitch() {
  const t = useT(shell);
  const lang = useLang();
  return (
    <ToggleButtonGroup size="sm" aria-label={t('language')} selectionMode="single" disallowEmptySelection
      selectedKeys={[lang]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setLang(next as Lang); }}>
      {LANGS.map((l, i) => (
        <ToggleButton key={l} id={l} className="min-w-10 font-semibold">
          {i > 0 ? <ToggleButtonGroup.Separator /> : null}
          {l.toUpperCase()}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}

const THEMES: { id: ThemePref, icon: LucideIcon, label: ShellKey }[] = [
  { id: 'light', icon: Sun, label: 'themeLight' },
  { id: 'dark', icon: Moon, label: 'themeDark' },
  { id: 'system', icon: Monitor, label: 'themeSystem' },
];

export function ThemeSwitch() {
  const t = useT(shell);
  const { pref } = useTheme();
  return (
    <ToggleButtonGroup size="sm" aria-label={t('theme')} selectionMode="single" disallowEmptySelection
      selectedKeys={[pref]} onSelectionChange={(keys) => { const next = [...keys][0]; if (next) setThemePref(next as ThemePref); }}>
      {THEMES.map((item, i) => (
        <Tooltip key={item.id} delay={200}>
          <ToggleButton id={item.id} isIconOnly aria-label={t(item.label)}>
            {i > 0 ? <ToggleButtonGroup.Separator /> : null}
            <item.icon className="size-4" />
          </ToggleButton>
          <Tooltip.Content>{t(item.label)}</Tooltip.Content>
        </Tooltip>
      ))}
    </ToggleButtonGroup>
  );
}
