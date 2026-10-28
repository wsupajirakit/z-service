// A stable look for a named thing (watchlist, ticker): two-letter initials and a tint picked
// from the name, so the same list always wears the same colour.

// Full class strings so Tailwind keeps them; each reads on light and dark.
const TINTS = [
  'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  'bg-rose-500/15 text-rose-700 dark:text-rose-300',
  'bg-indigo-500/15 text-indigo-700 dark:text-indigo-300',
  'bg-teal-500/15 text-teal-700 dark:text-teal-300',
  'bg-orange-500/15 text-orange-700 dark:text-orange-300',
  'bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300',
  'bg-lime-500/15 text-lime-700 dark:text-lime-300',
];

function hash(text: string) {
  let h = 0;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

export function tintFor(name: string) {
  return TINTS[hash(name) % TINTS.length];
}

/** "BNECK-3THEMES-1022" -> "B3", "CORE-INDEX-1023" -> "CI", "Default" -> "DE". */
export function initialsFor(name: string) {
  const parts = splitListName(name).base.split(/[\s_\-.]+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : (parts[0] ?? name).slice(0, 2);
  return letters.toUpperCase() || '?';
}

export type ListName = { base: string; date: { month: number; day: number } | null };

/** Lists named like "TOPIC-1022" carry their creation date (MMDD) at the end. */
export function splitListName(name: string): ListName {
  const m = /^(.*?)[-_ ](\d{2})(\d{2})$/.exec(name);
  if (m) {
    const month = Number(m[2]);
    const day = Number(m[3]);
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) return { base: m[1], date: { month, day } };
  }
  return { base: name, date: null };
}
