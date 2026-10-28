import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

// Card header row: tinted icon tile, title, short description and actions on the right.
export function SectionHeader({ icon: Icon, tint = 'bg-accent-soft text-accent-soft-foreground', title, description, actions }: {
  icon: LucideIcon;
  tint?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${tint}`}>
          <Icon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-foreground">{title}</h2>
          {description ? <p className="text-sm text-muted">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
