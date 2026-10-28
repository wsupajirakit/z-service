import { useState } from 'react'
import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardFooter, CardHeader } from '../../../components/ui/Card.tsx'
import { ConfirmAction } from '../../../components/ui/ConfirmAction.tsx'
import { ChartIcon, PlayIcon } from '../../../components/ui/icons.tsx'
import { SymbolPicker } from '../../../components/ui/SymbolPicker.tsx'
import { earningScanAction } from '../api.ts'

export function EarningScanForm({ defaultOpen, initial = [] }: {
  defaultOpen?: boolean
  initial?: string[]
}) {
  const scan = useAction(earningScanAction,
    { success: (d) => m.earning_scan_done({ count: d.results.length }) })
  const [picked, setPicked] = useState<string[]>(initial)
  return (
    <Card testId="earning-scan">
      <CardHeader icon={ChartIcon} title={m.earning_scan_title()}
        description={m.earning_scan_description()} />
      <CardContent>
        <SymbolPicker value={picked} onChange={setPicked} />
      </CardContent>
      <CardFooter>
        <ConfirmAction
          tone="cost"
          variant="default"
          icon={PlayIcon}
          label={m.earning_scan_start()}
          title={m.earning_scan_start()}
          details={m.earning_scan_details({ count: picked.length })}
          confirmLabel={m.earning_scan_start()}
          disabled={picked.length === 0 || scan.isPending}
          defaultOpen={defaultOpen}
          onConfirm={() => scan.mutate(picked)}
        />
        <ActionStatus action={scan} />
      </CardFooter>
    </Card>
  )
}
