import { m } from '../../../paraglide/messages.js'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { ChartIcon, HistoryIcon } from '../../../components/ui/icons.tsx'
import { PageHeader } from '../../../components/ui/PageHeader.tsx'
import { useRoundList } from '../api.ts'
import { pickStamp } from '../model.ts'
import { RunRound } from './RoundActions.tsx'
import { RoundDetail } from './RoundDetail.tsx'
import { RoundList } from './RoundList.tsx'
import { RoundStatusLine, TfStatusTable } from './StatusPanels.tsx'

type Props = { stamp: string | null; onSelect: (stamp: string) => void }

export function RadarSummaryPage({ stamp, onSelect }: Props) {
  const list = useRoundList()
  const stamps = list.data?.rounds.map((r) => r.stamp) ?? []
  const shown = pickStamp(stamps, stamp)
  return (
    <section className="space-y-6">
      <PageHeader description={m.page_desc_radar_summary()}>
        <RoundStatusLine />
      </PageHeader>
      <div className="grid gap-6 xl:grid-cols-2">
        <RunRound />
        <Card>
          <CardHeader icon={ChartIcon} title={m.radar_tf_title()} />
          <CardContent><TfStatusTable /></CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader icon={HistoryIcon} title={m.radar_rounds_title()} />
        <CardContent><RoundList selected={shown} onSelect={onSelect} /></CardContent>
      </Card>
      {shown && <RoundDetail stamp={shown} />}
    </section>
  )
}
