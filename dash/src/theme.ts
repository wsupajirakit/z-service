// Light / dark / system theme. HeroUI reads `class="dark"` or `data-theme` on <html>;
// public/theme-init.js applies the saved choice before the first paint (no flash).
import { useSyncExternalStore } from 'react';

export type ThemePref = 'light' | 'dark' | 'system';
export type Theme = 'light' | 'dark';
const KEY = 'zs.theme';
const media = window.matchMedia('(prefers-color-scheme: dark)');
const listeners = new Set<() => void>();

let pref: ThemePref = ((): ThemePref => {
  const saved = localStorage.getItem(KEY);
  return saved === 'light' || saved === 'dark' ? saved : 'system';
})();

function resolved(): Theme {
  return pref === 'system' ? (media.matches ? 'dark' : 'light') : pref;
}

function apply() {
  const theme = resolved();
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.classList.toggle('light', theme === 'light');
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  listeners.forEach((fn) => fn());
}

media.addEventListener('change', () => { if (pref === 'system') apply(); });
apply();

export function setThemePref(next: ThemePref) {
  pref = next;
  if (next === 'system') localStorage.removeItem(KEY);
  else localStorage.setItem(KEY, next);
  apply();
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

const snapshot = () => `${pref}:${resolved()}`;

export function useTheme(): { pref: ThemePref; theme: Theme } {
  const [p, t] = useSyncExternalStore(subscribe, snapshot).split(':');
  return { pref: p as ThemePref, theme: t as Theme };
}
