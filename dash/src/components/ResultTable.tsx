import { EmptyState, Pagination, Table } from '@heroui/react';
import { Inbox } from 'lucide-react';
import { useState } from 'react';
import { useLang, useT } from '../i18n';
import { widgets } from '../i18n/messages/widgets';
import type { TradeData } from '../lib';

const PAGE_SIZE = 100;

const signClass = (n: number) => (n > 0 ? 'text-success' : n < 0 ? 'text-danger' : 'text-muted');
const ipiClass = (status: string) =>
  status === 'Institutional Accumulation' ? 'text-success'
    : status === 'Institutional Distribution' ? 'text-danger'
      : 'text-warning';

// Price + indicator rows (Dashboard result and History records), 100 rows per page.
/** `height`: the scroll area's height class (the page around it decides). */
export function ResultTable({ data, height = 'max-h-[640px]' }: { data: TradeData[], height?: string }) {
  const t = useT(widgets);
  const lang = useLang();
  const loc = lang === 'th' ? 'th-TH' : 'en-US';
  // The page resets to 1 whenever a new data array arrives.
  const [paging, setPaging] = useState({ data, page: 1 });
  const page = paging.data === data ? paging.page : 1;
  const setPage = (p: number) => setPaging({ data, page: p });

  const pages = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
  const from = (page - 1) * PAGE_SIZE;
  const rows = data.slice(from, from + PAGE_SIZE).map((row, i) => ({ ...row, id: from + i }));

  const num = (v: number | null, min: number, max: number) =>
    v ? v.toLocaleString(loc, { minimumFractionDigits: min, maximumFractionDigits: max }) : '-';

  const cell = 'text-right font-mono tabular-nums whitespace-nowrap';
  return (
    <div className="space-y-3">
      <Table>
        <Table.ScrollContainer className={`${height} overflow-auto`}>
          <Table.Content aria-label={t('tableLabel')} className="min-w-[1400px] text-sm">
            <Table.Header className="sticky top-0 z-10 [&_th]:whitespace-nowrap">
              <Table.Column isRowHeader className="whitespace-nowrap">{t('colDatetime')}</Table.Column>
              <Table.Column className="text-right">{t('colClose')}</Table.Column>
              <Table.Column className="text-right">{t('colVolume')}</Table.Column>
              <Table.Column className="text-right">EMA 20</Table.Column>
              <Table.Column className="text-right">EMA 50</Table.Column>
              <Table.Column className="text-right">EMA 100</Table.Column>
              <Table.Column className="text-right">EMA 200</Table.Column>
              <Table.Column className="text-right">RSI (14)</Table.Column>
              <Table.Column className="text-right">OBV</Table.Column>
              <Table.Column className="text-right">CMF</Table.Column>
              <Table.Column className="text-right">VWAP</Table.Column>
              <Table.Column className="text-center">FVG</Table.Column>
              <Table.Column className="text-right">RVOL</Table.Column>
              <Table.Column className="text-right">{t('colVolDev')}</Table.Column>
              <Table.Column className="text-right">IPI</Table.Column>
              <Table.Column className="text-right">{t('colIpiStatus')}</Table.Column>
            </Table.Header>
            <Table.Body
              items={rows}
              renderEmptyState={() => (
                <EmptyState className="flex flex-col items-center justify-center gap-2 py-12 text-sm text-muted">
                  <Inbox className="size-6" />
                  {t('tableEmpty')}
                </EmptyState>
              )}
            >
              {(row) => (
                <Table.Row id={row.id}>
                  <Table.Cell className="whitespace-nowrap font-mono text-muted">{row.datetime}</Table.Cell>
                  <Table.Cell className={`${cell} font-medium text-foreground`}>
                    {row.close.toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                  </Table.Cell>
                  <Table.Cell className={`${cell} text-muted`}>{num(row.volume, 0, 0)}</Table.Cell>
                  <Table.Cell className={`${cell} text-blue-600 dark:text-blue-400`}>{num(row.EMA_20, 2, 6)}</Table.Cell>
                  <Table.Cell className={`${cell} text-purple-600 dark:text-purple-400`}>{num(row.EMA_50, 2, 6)}</Table.Cell>
                  <Table.Cell className={`${cell} text-teal-600 dark:text-teal-400`}>{num(row.EMA_100, 2, 6)}</Table.Cell>
                  <Table.Cell className={`${cell} text-orange-600 dark:text-orange-400`}>{num(row.EMA_200, 2, 6)}</Table.Cell>
                  <Table.Cell className={`${cell} font-semibold text-rose-600 dark:text-rose-400`}>{num(row.RSI, 2, 2)}</Table.Cell>
                  <Table.Cell className={cell}>{num(row.OBV, 0, 0)}</Table.Cell>
                  <Table.Cell className={cell}>{num(row.CMF, 2, 4)}</Table.Cell>
                  <Table.Cell className={`${cell} font-medium text-indigo-600 dark:text-indigo-400`}>{num(row.VWAP, 2, 6)}</Table.Cell>
                  <Table.Cell className="text-center font-mono tabular-nums font-medium">
                    {row.FVG !== null ? (
                      <span className={signClass(row.FVG)}>
                        {row.FVG > 0 ? '+' : ''}{row.FVG.toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                      </span>
                    ) : '-'}
                  </Table.Cell>
                  <Table.Cell className={`${cell} font-medium`}>{num(row.RVOL, 2, 2)}</Table.Cell>
                  <Table.Cell className={`${cell} font-medium`}>
                    {row.RVOL_Deviation !== null ? (
                      <span className={row.RVOL_Deviation > 0 ? 'text-success' : 'text-danger'}>
                        {row.RVOL_Deviation > 0 ? '+' : ''}
                        {row.RVOL_Deviation.toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%
                      </span>
                    ) : '-'}
                  </Table.Cell>
                  <Table.Cell className={`${cell} font-bold text-accent`}>
                    {row.IPI !== null ? row.IPI.toLocaleString(loc, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '-'}
                  </Table.Cell>
                  <Table.Cell className="text-right whitespace-nowrap font-semibold">
                    {row.IPI_Status ? <span className={ipiClass(row.IPI_Status)}>{row.IPI_Status}</span> : '-'}
                  </Table.Cell>
                </Table.Row>
              )}
            </Table.Body>
          </Table.Content>
        </Table.ScrollContainer>
      </Table>
      {pages > 1 ? (
        <Pagination className="w-full">
          <Pagination.Summary>
            {t('pageSummary', {
              from: (from + 1).toLocaleString(loc),
              to: Math.min(from + PAGE_SIZE, data.length).toLocaleString(loc),
              total: data.length.toLocaleString(loc),
            })}
          </Pagination.Summary>
          <Pagination.Content>
            <Pagination.Item>
              <Pagination.Previous isDisabled={page === 1} onPress={() => setPage(page - 1)}>
                <Pagination.PreviousIcon />
                <span>{t('pagePrev')}</span>
              </Pagination.Previous>
            </Pagination.Item>
            <Pagination.Item>
              <span className="px-2 text-sm text-muted">{t('pageOf', { page, pages })}</span>
            </Pagination.Item>
            <Pagination.Item>
              <Pagination.Next isDisabled={page === pages} onPress={() => setPage(page + 1)}>
                <span>{t('pageNext')}</span>
                <Pagination.NextIcon />
              </Pagination.Next>
            </Pagination.Item>
          </Pagination.Content>
        </Pagination>
      ) : null}
    </div>
  );
}
