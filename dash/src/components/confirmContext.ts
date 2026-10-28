import { createContext, useContext, type ReactNode } from 'react';

export type ConfirmOptions = {
  title: string;
  body?: ReactNode;
  confirmLabel?: string;
  tone?: 'danger' | 'accent';
};

export type Ask = (options: ConfirmOptions) => Promise<boolean>;
export const ConfirmContext = createContext<Ask | null>(null);

/** `if (!(await confirm({ title }))) return;` (needs <ConfirmProvider> above). */
export function useConfirm(): Ask {
  const ask = useContext(ConfirmContext);
  if (!ask) throw new Error('useConfirm needs <ConfirmProvider>');
  return ask;
}
