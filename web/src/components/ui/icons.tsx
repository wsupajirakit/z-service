// Icons as plain SVG elements. lucide-react's runtime (createLucideIcon and helpers) costs
// ~3 KB gzip on first load, so the path data is copied here instead. Paths are from Lucide
// (ISC license, https://lucide.dev), unchanged. Each export is marked pure so an icon no page
// uses is dropped from the bundle.
import { createElement, type ReactElement } from 'react'

export type IconProps = { size?: number; className?: string }
export type IconComponent = (props: IconProps) => ReactElement
type IconNode = string | readonly [string, Readonly<Record<string, number | string>>]

/** A path is written as its `d` string; any other element as [tag, attributes]. */
function icon(nodes: readonly IconNode[]): IconComponent {
  return function Icon({ size = 16, className }: IconProps) {
    return (
      <svg
        aria-hidden
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className ? `shrink-0 ${className}` : 'shrink-0'}
      >
        {nodes.map((n, i) => (typeof n === 'string'
          ? <path key={i} d={n} />
          : createElement(n[0], { key: i, ...n[1] })))}
      </svg>
    )
  }
}

export const SunIcon = /* @__PURE__ */ icon([
  ['circle', { cx: 12, cy: 12, r: 4 }],
  'M12 2v2',
  'M12 20v2',
  'm4.93 4.93 1.41 1.41',
  'm17.66 17.66 1.41 1.41',
  'M2 12h2',
  'M20 12h2',
  'm6.34 17.66-1.41 1.41',
  'm19.07 4.93-1.41 1.41',
])
export const MoonIcon = /* @__PURE__ */ icon([
  'M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 '
    + '8.268c.344-.215.825-.004.803.401',
])
export const MenuIcon = /* @__PURE__ */ icon(['M4 5h16', 'M4 12h16', 'M4 19h16'])
export const PanelLeftIcon = /* @__PURE__ */ icon([
  ['rect', { width: 18, height: 18, x: 3, y: 3, rx: 2 }],
  'M9 3v18',
])
export const LanguagesIcon = /* @__PURE__ */ icon([
  'm5 8 6 6',
  'm4 14 6-6 2-3',
  'M2 5h12',
  'M7 2h1',
  'm22 22-5-10-5 10',
  'M14 18h6',
])
export const LogOutIcon = /* @__PURE__ */ icon([
  'm16 17 5-5-5-5',
  'M21 12H9',
  'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4',
])
export const ChevronDownIcon = /* @__PURE__ */ icon(['m6 9 6 6 6-6'])
export const ChevronLeftIcon = /* @__PURE__ */ icon(['m15 18-6-6 6-6'])
export const ChevronRightIcon = /* @__PURE__ */ icon(['m9 18 6-6-6-6'])
export const ChevronsUpDownIcon = /* @__PURE__ */ icon(['m7 15 5 5 5-5', 'm7 9 5-5 5 5'])
export const ArrowUpIcon = /* @__PURE__ */ icon(['m5 12 7-7 7 7', 'M12 19V5'])
export const ArrowDownIcon = /* @__PURE__ */ icon(['M12 5v14', 'm19 12-7 7-7-7'])
export const SearchIcon = /* @__PURE__ */ icon([
  'm21 21-4.34-4.34',
  ['circle', { cx: 11, cy: 11, r: 8 }],
])
export const XIcon = /* @__PURE__ */ icon(['M18 6 6 18', 'm6 6 12 12'])
export const CheckIcon = /* @__PURE__ */ icon(['M20 6 9 17l-5-5'])
export const AlertIcon = /* @__PURE__ */ icon([
  'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3',
  'M12 9v4',
  'M12 17h.01',
])
export const InfoIcon = /* @__PURE__ */ icon([
  ['circle', { cx: 12, cy: 12, r: 10 }],
  'M12 16v-4',
  'M12 8h.01',
])
export const CircleCheckIcon = /* @__PURE__ */ icon([
  ['circle', { cx: 12, cy: 12, r: 10 }],
  'm9 12 2 2 4-4',
])
export const LoaderIcon = /* @__PURE__ */ icon(['M21 12a9 9 0 1 1-6.219-8.56'])
export const InboxIcon = /* @__PURE__ */ icon([
  ['polyline', { points: '22 12 16 12 14 15 10 15 8 12 2 12' }],
  'M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 '
    + '4H7.24a2 2 0 0 0-1.79 1.11z',
])
export const UserIcon = /* @__PURE__ */ icon([
  'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2',
  ['circle', { cx: 12, cy: 7, r: 4 }],
])
export const HomeIcon = /* @__PURE__ */ icon([
  ['rect', { width: 7, height: 9, x: 3, y: 3, rx: 1 }],
  ['rect', { width: 7, height: 5, x: 14, y: 3, rx: 1 }],
  ['rect', { width: 7, height: 9, x: 14, y: 12, rx: 1 }],
  ['rect', { width: 7, height: 5, x: 3, y: 16, rx: 1 }],
])
export const ActivityIcon = /* @__PURE__ */ icon([
  'M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 '
    + '0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2',
])
export const ListIcon = /* @__PURE__ */ icon([
  'M13 5h8',
  'M13 12h8',
  'M13 19h8',
  'm3 17 2 2 4-4',
  'm3 7 2 2 4-4',
])
export const BriefcaseIcon = /* @__PURE__ */ icon([
  'M12 12h.01',
  'M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2',
  'M22 13a18.15 18.15 0 0 1-20 0',
  ['rect', { width: 20, height: 14, x: 2, y: 6, rx: 2 }],
])
export const HistoryIcon = /* @__PURE__ */ icon([
  'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8',
  'M3 3v5h5',
  'M12 7v5l4 2',
])
export const DownloadIcon = /* @__PURE__ */ icon([
  'M12 15V3',
  'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4',
  'm7 10 5 5 5-5',
])
export const RadarIcon = /* @__PURE__ */ icon([
  'M19.07 4.93A10 10 0 0 0 6.99 3.34',
  'M4 6h.01',
  'M2.29 9.62A10 10 0 1 0 21.31 8.35',
  'M16.24 7.76A6 6 0 1 0 8.23 16.67',
  'M12 18h.01',
  'M17.99 11.66A6 6 0 0 1 15.77 16.67',
  ['circle', { cx: 12, cy: 12, r: 2 }],
  'm13.41 10.59 5.66-5.66',
])
export const ScanIcon = /* @__PURE__ */ icon([
  'M3 7V5a2 2 0 0 1 2-2h2',
  'M17 3h2a2 2 0 0 1 2 2v2',
  'M21 17v2a2 2 0 0 1-2 2h-2',
  'M7 21H5a2 2 0 0 1-2-2v-2',
  ['circle', { cx: 12, cy: 12, r: 3 }],
  'm16 16-1.9-1.9',
])
export const ChartIcon = /* @__PURE__ */ icon([
  'M3 3v16a2 2 0 0 0 2 2h16',
  'M18 17V9',
  'M13 17V5',
  'M8 17v-3',
])
export const CoinsIcon = /* @__PURE__ */ icon([
  'M13.744 17.736a6 6 0 1 1-7.48-7.48',
  'M15 6h1v4',
  'm6.134 14.768.866-.5 2 3.464',
  ['circle', { cx: 16, cy: 8, r: 6 }],
])
export const SettingsIcon = /* @__PURE__ */ icon([
  'M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 '
    + '2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 '
    + '1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 '
    + '2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915',
  ['circle', { cx: 12, cy: 12, r: 3 }],
])
export const MailIcon = /* @__PURE__ */ icon([
  'M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 '
    + '.8-1.6l8-6a2 2 0 0 1 2.4 0l8 6Z',
  'm22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10',
])
export const PlusIcon = /* @__PURE__ */ icon(['M5 12h14', 'M12 5v14'])
export const PencilIcon = /* @__PURE__ */ icon([
  'M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 '
    + '0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z',
  'm15 5 4 4',
])
export const TrashIcon = /* @__PURE__ */ icon([
  'M10 11v6',
  'M14 11v6',
  'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6',
  'M3 6h18',
  'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2',
])
export const ExternalLinkIcon = /* @__PURE__ */ icon([
  'M15 3h6v6',
  'M10 14 21 3',
  'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6',
])
export const RefreshIcon = /* @__PURE__ */ icon([
  'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8',
  'M21 3v5h-5',
  'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16',
  'M8 16H3v5',
])
export const PlayIcon = /* @__PURE__ */ icon([
  'M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z',
])
export const StopIcon = /* @__PURE__ */ icon([
  ['rect', { width: 18, height: 18, x: 3, y: 3, rx: 2 }],
])
