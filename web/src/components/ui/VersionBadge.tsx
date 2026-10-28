import { m } from '../../paraglide/messages.js'
import { useVersion } from '../../services/api/common.ts'

export function VersionBadge() {
  const { data } = useVersion()
  if (!data) return null
  return (
    <span className="rounded-md border px-2 py-0.5 font-mono text-xs text-muted-foreground"
      data-testid="version">
      {m.version_badge({ version: data.version, commit: (data.commit ?? '').slice(0, 7) })}
    </span>
  )
}
