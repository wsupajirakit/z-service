// Phase 0 browser probe. Bundled only with `vite build --mode selftest`; production drops it.
import { changeLocale } from '../stores/locale.ts'
import { setTheme } from '../stores/theme.ts'

type Report = Record<string, unknown>
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))
const text = (sel: string) => document.querySelector(sel)?.textContent ?? null
const violations: string[] = []

document.addEventListener('securitypolicyviolation', (e) => {
  violations.push(`${e.violatedDirective} blocked=${e.blockedURI} sample=${e.sample}`)
})

async function probeLocale(r: Report) {
  const counter = document.querySelector<HTMLButtonElement>('[data-testid=counter]')
  counter?.click()
  counter?.click()
  await wait(100)
  r.initialLocale = document.documentElement.lang
  changeLocale('th')
  await wait(50)
  r.before = { intro: text('[data-testid=intro]'), counter: text('[data-testid=counter]') }
  const marker = Math.random()
  ;(window as unknown as { __marker: number }).__marker = marker
  const t0 = performance.now()
  changeLocale('en')
  await wait(50)
  r.after = {
    intro: text('[data-testid=intro]'),
    counter: text('[data-testid=counter]'),
    nav: text('[data-testid=nav]'),
    lang: document.documentElement.lang,
    sameDocument: (window as unknown as { __marker: number }).__marker === marker,
    switchMs: Math.round(performance.now() - t0),
  }
  changeLocale('it')
  await wait(50)
  r.afterIt = { intro: text('[data-testid=intro]'), nav: text('[data-testid=nav]') }
}

async function probeTheme(r: Report) {
  setTheme('dark')
  await wait(50)
  r.dark = {
    attr: document.documentElement.dataset.theme,
    bg: getComputedStyle(document.body).backgroundColor,
  }
  setTheme('light')
  await wait(50)
  r.light = {
    attr: document.documentElement.dataset.theme,
    bg: getComputedStyle(document.body).backgroundColor,
  }
}

async function probeTable(r: Report) {
  r.rowsInDom = document.querySelectorAll('tr[data-row]').length
  r.firstBefore = text('tr[data-row] td:nth-child(2)')
  const priceHeader = document.querySelectorAll<HTMLButtonElement>('th button')[1]
  priceHeader?.click()
  await wait(100)
  r.firstAfterSort1 = text('tr[data-row] td:nth-child(2)')
  priceHeader?.click()
  await wait(100)
  r.firstAfterSort2 = text('tr[data-row] td:nth-child(2)')
  r.rowCountLabel = text('[data-testid=table-range]')
}

export async function runSelfTest() {
  await wait(800)
  const r: Report = { path: location.pathname }
  r.links = [...document.querySelectorAll('nav a')].map((a) => a.getAttribute('href'))
  r.cssLinks = document.querySelectorAll('link[rel=stylesheet]').length
  r.tailwindApplied = getComputedStyle(document.querySelector('header') ?? document.body).display
  if (document.querySelector('[data-testid=counter]')) await probeLocale(r)
  if (document.querySelector('[data-testid=table]')) await probeTable(r)
  if (document.querySelector('[data-testid=chart]')) {
    await wait(800)
    r.chartCanvases = document.querySelectorAll('[data-testid=chart] canvas').length
    await probeTheme(r)
  }
  r.violations = violations
  const out = document.createElement('pre')
  out.id = 'selftest'
  out.textContent = JSON.stringify(r)
  document.body.append(out)
}
