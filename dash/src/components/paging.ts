import { useState } from 'react';

/** Client-side paging of a list: the page is clamped when the list shrinks (a filter). */
export function usePaged<T>(items: T[], initialSize = 25) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeState] = useState(initialSize);
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(page, pageCount);
  const start = (current - 1) * pageSize;
  const setPageSize = (size: number) => { setPageSizeState(size); setPage(1); };
  return {
    page: current, setPage, pageSize, setPageSize, pageCount, total,
    from: total ? start + 1 : 0, to: Math.min(start + pageSize, total),
    pageItems: items.slice(start, start + pageSize),
  };
}

/** Page numbers to show: first, last, the current one and its neighbours; gaps as null. */
export function pageWindow(page: number, pageCount: number): (number | null)[] {
  const wanted = new Set([1, pageCount, page - 1, page, page + 1].filter((p) => p >= 1 && p <= pageCount));
  const sorted = [...wanted].sort((a, b) => a - b);
  const out: (number | null)[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push(null);
    out.push(p);
  });
  return out;
}
