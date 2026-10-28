// Themed notifications in place of window.alert (the <Toast.Provider /> sits in App).
import { toast } from '@heroui/react';

export const notify = {
  success: (text: string) => toast.success(text),
  error: (text: string) => toast.danger(text),
  warning: (text: string) => toast.warning(text),
  info: (text: string) => toast.info(text),
};

/** The server's message for a failed request, else the error's own. */
export function errorDetail(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown; error?: { message?: string } } }; message?: string };
  const detail = e?.response?.data?.detail ?? e?.response?.data?.error?.message;
  if (typeof detail === 'string') return detail;
  if (detail) return JSON.stringify(detail);
  return e?.message ?? String(err);
}
