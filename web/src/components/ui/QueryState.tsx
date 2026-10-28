import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { m } from '../../paraglide/messages.js'
import { errorText } from '../../services/api/errorMessages.ts'
import { Alert, EmptyState, Skeleton } from './Feedback.tsx'

/** Loading / error / empty states around a query, so pages only render data. */
export function QueryState<T>({ query, isEmpty, children }: {
  query: UseQueryResult<T>
  isEmpty?: (data: T) => boolean
  children: (data: T) => ReactNode
}) {
  if (query.isPending) return <Skeleton />
  if (query.isError) {
    return <Alert tone="destructive" title={m.state_error()}>{errorText(query.error)}</Alert>
  }
  if (isEmpty?.(query.data)) return <EmptyState />
  return <>{children(query.data)}</>
}
