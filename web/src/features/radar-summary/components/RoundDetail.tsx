import { m } from '../../../paraglide/messages.js'
import { MarkdownText } from '../../../components/MarkdownText.tsx'
import { useFormat } from '../../../hooks/useFormat.ts'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { Alert, EmptyState } from '../../../components/ui/Feedback.tsx'
import { QueryState } from '../../../components/ui/QueryState.tsx'
import { useRoundDetail } from '../api.ts'
import { roundWarnings } from '../model.ts'
import { DeleteRound } from './RoundActions.tsx'

export function RoundDetail({ stamp }: { stamp: string }) {
  const query = useRoundDetail(stamp)
  const fmt = useFormat()
  return (
    <Card testId="round-detail">
      <QueryState query={query}>
        {(round) => (
          <>
            <CardHeader
              title={m.radar_round_title({ stamp: round.stamp })}
              description={m.radar_round_meta({
                created: fmt.dateTime(round.created_at),
                breadth: fmt.number(round.breadth_n, 0),
                kill: round.kill_label ?? '',
              })}
              actions={<DeleteRound key={round.stamp} stamp={round.stamp} />}
            />
            <CardContent className="space-y-3">
              {roundWarnings(round).map((w, i) => (
                <Alert key={i} tone="warning">{w}</Alert>
              ))}
              {round.digest_md ? <MarkdownText source={round.digest_md} /> : <EmptyState />}
            </CardContent>
          </>
        )}
      </QueryState>
    </Card>
  )
}
