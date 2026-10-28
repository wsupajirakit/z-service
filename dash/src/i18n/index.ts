// EN/TH labels. Each page keeps its own message table (src/i18n/messages/<page>.ts) built
// with defineMessages, which makes the Thai table carry exactly the English keys (a missing
// or extra key fails the type check). The language switches at once and is remembered.
import { useSyncExternalStore } from 'react';

export type Lang = 'en' | 'th';
export const LANGS: Lang[] = ['en', 'th'];
const KEY = 'zs.lang';
const listeners = new Set<() => void>();

function initial(): Lang {
  const saved = localStorage.getItem(KEY);
  if (saved === 'en' || saved === 'th') return saved;
  return navigator.language.toLowerCase().startsWith('th') ? 'th' : 'en';
}

let current: Lang = initial();
document.documentElement.lang = current;

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang) {
  current = lang;
  localStorage.setItem(KEY, lang);
  document.documentElement.lang = lang;
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang);
}

type Table<K extends string> = Record<K, string>;
export type Messages<K extends string> = { en: Table<K>; th: Table<K> };
type Vars = Record<string, string | number>;
/** The keys of a message table: `MessageKey<typeof shell>`. */
export type MessageKey<M> = M extends Messages<infer K> ? K : never;

export function defineMessages<const E extends Record<string, string>>(
  messages: { en: E; th: { [K in keyof E]: string } },
): Messages<Extract<keyof E, string>> {
  return messages as Messages<Extract<keyof E, string>>;
}

function format(text: string, vars?: Vars) {
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (all, name: string) => (name in vars ? String(vars[name]) : all));
}

/** `t(key, { n: 3 })` for the current language; `{name}` placeholders are filled in. */
export function useT<K extends string>(messages: Messages<K>) {
  const lang = useLang();
  return (key: K, vars?: Vars) => format(messages[lang][key], vars);
}

/** The same lookup outside a component (reads the language at call time). */
export function translate<K extends string>(messages: Messages<K>, key: K, vars?: Vars) {
  return format(messages[current][key], vars);
}
