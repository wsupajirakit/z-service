import { AlertDialog, Button } from '@heroui/react';
import { useCallback, useRef, useState, type ReactNode } from 'react';
import { useT } from '../i18n';
import { common } from '../i18n/messages/common';
import { ConfirmContext, type Ask, type ConfirmOptions } from './confirmContext';


/** One themed confirmation dialog for the whole app, in place of window.confirm. */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const t = useT(common);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<(ok: boolean) => void>(() => undefined);
  const ask = useCallback<Ask>((next) => new Promise<boolean>((resolve) => {
    resolver.current = resolve;
    setOptions(next);
  }), []);
  const finish = (ok: boolean) => {
    resolver.current(ok);
    setOptions(null);
  };
  const tone = options?.tone ?? 'danger';
  return (
    <ConfirmContext.Provider value={ask}>
      {children}
      <AlertDialog.Backdrop isOpen={options !== null} onOpenChange={(open) => { if (!open) finish(false); }}>
        <AlertDialog.Container>
          <AlertDialog.Dialog className="sm:max-w-[420px]">
            <AlertDialog.Header>
              <AlertDialog.Icon status={tone} />
              <AlertDialog.Heading>{options?.title}</AlertDialog.Heading>
            </AlertDialog.Header>
            {options?.body ? <AlertDialog.Body>{options.body}</AlertDialog.Body> : null}
            <AlertDialog.Footer>
              <Button variant="tertiary" onPress={() => finish(false)}>{t('cancel')}</Button>
              <Button variant={tone === 'danger' ? 'danger' : 'primary'} onPress={() => finish(true)}>
                {options?.confirmLabel ?? t('confirm')}
              </Button>
            </AlertDialog.Footer>
          </AlertDialog.Dialog>
        </AlertDialog.Container>
      </AlertDialog.Backdrop>
    </ConfirmContext.Provider>
  );
}

