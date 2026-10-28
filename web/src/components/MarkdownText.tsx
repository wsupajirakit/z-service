// The only markdown renderer in the app (lint bans importing markdown-to-jsx elsewhere).
// Raw HTML in the source is never parsed into elements; the library's built-in URL sanitizer
// drops javascript:/vbscript:/data: links.
import Markdown from 'markdown-to-jsx'

export const markdownOptions = { disableParsingRawHTML: true } as const

export function MarkdownText({ source }: { source: string }) {
  return (
    <div className="markdown space-y-2 text-sm">
      <Markdown options={markdownOptions}>{source}</Markdown>
    </div>
  )
}
