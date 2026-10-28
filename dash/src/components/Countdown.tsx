import { useEffect, useState } from 'react';

// Self-contained countdown: re-renders only itself each second, computed from an
// absolute server timestamp so it stays correct after closing/reopening the tab.
export function Countdown({ until }: { until: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const remaining = Math.max(0, Math.round((until - now) / 1000));
  const m = Math.floor(remaining / 60).toString().padStart(2, '0');
  const s = (remaining % 60).toString().padStart(2, '0');
  return <span className="font-mono tabular-nums">{m}:{s}</span>;
}
