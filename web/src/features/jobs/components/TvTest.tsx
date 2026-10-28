import { m } from '../../../paraglide/messages.js'
import { useAction } from '../../../services/api/action.ts'
import { serverText } from '../../../services/api/serverMessages.ts'
import { ActionStatus } from '../../../components/ui/ActionStatus.tsx'
import { Card, CardContent, CardHeader } from '../../../components/ui/Card.tsx'
import { Alert } from '../../../components/ui/Feedback.tsx'
import { button } from '../../../components/ui/form.ts'
import { PlayIcon, RadarIcon } from '../../../components/ui/icons.tsx'
import { tvTestAction } from '../api.ts'
import type { TvTest as TvTestResult } from '../schemas.ts'

const levelClass = (level: string) =>
  level === 'error' ? 'text-destructive' : level === 'ok' ? 'text-up' : 'text-muted-foreground'

export function TvTestReport({ result }: { result: TvTestResult }) {
  return (
    <div className="space-y-3 text-sm" data-testid="tv-test">
      <Alert tone={result.ok ? 'success' : 'destructive'}
        title={m.tv_test_verdict({
          verdict: serverText({ code: result.verdict_code, text: result.verdict }),
          passed: result.passed ?? 0,
          total: result.total ?? 0,
        })} />
      <ul className="max-h-60 space-y-0.5 overflow-auto rounded-lg border bg-muted/40 p-3
        font-mono text-xs">
        {result.logs.map((l, i) => (
          <li key={i} className={levelClass(l.level)}>
            {`${l.time} ${serverText({ code: l.code, params: l.params, text: l.message })}`}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function TvTest() {
  const test = useAction(tvTestAction)
  return (
    <Card>
      <CardHeader icon={RadarIcon} title={m.tv_test_title()} description={m.tv_test_description()}
        actions={(
          <button type="button" className={button('outline', 'sm')} disabled={test.isPending}
            onClick={() => test.mutate()}>
            <PlayIcon />
            {m.tv_test_run()}
          </button>
        )} />
      {(test.status !== 'idle') && (
        <CardContent>
          {test.status === 'success' ? <TvTestReport result={test.data} />
            : <ActionStatus action={test} />}
        </CardContent>
      )}
    </Card>
  )
}
