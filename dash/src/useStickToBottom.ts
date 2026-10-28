import { useEffect, useRef } from 'react';

// Keep a log box scrolled to its newest line by moving only the box's own scrollTop, never
// the page (scrollIntoView scrolls every scrollable ancestor, the window included). Stops
// following while the reader has scrolled up, and resumes once they are back at the bottom.
const NEAR_BOTTOM_PX = 24;

export function useStickToBottom<T>(content: T) {
  const box = useRef<HTMLDivElement>(null);
  const follow = useRef(true);
  useEffect(() => {
    const el = box.current;
    if (el && follow.current) el.scrollTop = el.scrollHeight;
  }, [content]);
  const onScroll = () => {
    const el = box.current;
    if (el) follow.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  };
  return { ref: box, onScroll };
}
