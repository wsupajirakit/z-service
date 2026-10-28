import { AlertDialog, Button } from '@heroui/react';
import { useT } from '../i18n';
import { common } from '../i18n/messages/common';

export interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'info' | 'danger' | 'warning' | 'success';
  onConfirm: () => void;
  onCancel: () => void;
}

const STATUS = { info: 'accent', danger: 'danger', warning: 'warning', success: 'success' } as const;

/** Controlled confirmation dialog; confirming runs onConfirm and then closes via onCancel. */
export function ConfirmationModal({
  isOpen, title, message, confirmText, cancelText, type = 'info', onConfirm, onCancel,
}: ConfirmationModalProps) {
  const t = useT(common);
  return (
    <AlertDialog.Backdrop isOpen={isOpen} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <AlertDialog.Container>
        <AlertDialog.Dialog className="sm:max-w-[440px]">
          <AlertDialog.Header>
            <AlertDialog.Icon status={STATUS[type]} />
            <AlertDialog.Heading>{title}</AlertDialog.Heading>
          </AlertDialog.Header>
          <AlertDialog.Body>
            <p className="whitespace-pre-line text-sm leading-relaxed text-muted">{message}</p>
          </AlertDialog.Body>
          <AlertDialog.Footer>
            <Button variant="tertiary" onPress={onCancel}>{cancelText ?? t('cancel')}</Button>
            <Button
              variant={type === 'danger' ? 'danger' : 'primary'}
              onPress={() => { onConfirm(); onCancel(); }}
            >
              {confirmText ?? t('confirm')}
            </Button>
          </AlertDialog.Footer>
        </AlertDialog.Dialog>
      </AlertDialog.Container>
    </AlertDialog.Backdrop>
  );
}
