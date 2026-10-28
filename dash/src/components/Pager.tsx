import { Label, ListBox, Pagination, Select } from '@heroui/react';
import { useT } from '../i18n';
import { common } from '../i18n/messages/common';
import { pageWindow } from './paging';

const SIZES = [10, 25, 50, 100];

/** "Showing 1–25 of 812" · page numbers with gaps · rows per page. Hidden when it all fits. */
export function Pager({ page, pageCount, total, from, to, pageSize, onPage, onPageSize, sizes = SIZES }: {
  page: number, pageCount: number, total: number, from: number, to: number, pageSize: number,
  onPage: (page: number) => void, onPageSize: (size: number) => void, sizes?: number[],
}) {
  const t = useT(common);
  if (total <= sizes[0]) return null;
  return (
    <div className="flex flex-col gap-3 border-t border-separator px-1 pt-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="whitespace-nowrap text-xs text-muted">{t('pagerSummary', { from, to, total })}</span>
        <Select aria-label={t('perPage')} value={pageSize} className="flex flex-row items-center gap-2"
          onChange={(v) => { if (v != null) onPageSize(Number(v)); }}>
          <Label className="whitespace-nowrap text-xs font-normal text-muted">{t('perPage')}</Label>
          <Select.Trigger className="h-8 min-w-[4.5rem] whitespace-nowrap font-mono text-xs">
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover className="min-w-[5rem]">
            <ListBox>
              {sizes.map((s) => (
                <ListBox.Item key={s} id={s} textValue={`${s}`} className="font-mono">{s}<ListBox.ItemIndicator /></ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
      {pageCount > 1 ? (
        <Pagination size="sm" className="shrink-0">
          <Pagination.Content aria-label={t('pagerPages')}>
            <Pagination.Item>
              <Pagination.Previous isDisabled={page === 1} onPress={() => onPage(page - 1)}>
                <Pagination.PreviousIcon /><span className="hidden sm:inline">{t('pagerPrev')}</span>
              </Pagination.Previous>
            </Pagination.Item>
            {pageWindow(page, pageCount).map((p, i) => (
              <Pagination.Item key={p ?? `gap-${i}`}>
                {p === null ? <Pagination.Ellipsis /> : (
                  <Pagination.Link isActive={p === page} onPress={() => onPage(p)}>{p}</Pagination.Link>
                )}
              </Pagination.Item>
            ))}
            <Pagination.Item>
              <Pagination.Next isDisabled={page === pageCount} onPress={() => onPage(page + 1)}>
                <span className="hidden sm:inline">{t('pagerNext')}</span><Pagination.NextIcon />
              </Pagination.Next>
            </Pagination.Item>
          </Pagination.Content>
        </Pagination>
      ) : null}
    </div>
  );
}
