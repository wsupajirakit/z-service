import { initialsFor, tintFor } from './listIdentity';

const SIZES = { sm: 'size-8 text-[11px] rounded-lg', md: 'size-10 text-xs rounded-xl', lg: 'size-14 text-base rounded-2xl' };

/** A rounded monogram for a watchlist or a ticker, tinted from its name. */
export function ListAvatar({ name, size = 'md', label }: { name: string, size?: keyof typeof SIZES, label?: string }) {
  return (
    <span aria-hidden={label ? undefined : true} aria-label={label} role={label ? 'img' : undefined}
      className={`grid shrink-0 place-items-center font-bold tracking-tight ring-1 ring-inset ring-current/15 ${SIZES[size]} ${tintFor(name)}`}>
      {initialsFor(name)}
    </span>
  );
}
