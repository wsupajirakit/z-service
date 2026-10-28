import { ComboBox, EmptyState, Input, Label, ListBox } from '@heroui/react';
import { useT } from '../i18n';
import { widgets } from '../i18n/messages/widgets';
import { ListAvatar } from './ListAvatar';

export type PickerSymbol = { symbol: string; exchange?: string };

/** Search and switch to another symbol, among the ones offered (e.g. the same fetch round). */
export function SymbolPicker({ symbols, value, onChange, className = 'w-full sm:w-64' }: {
  symbols: PickerSymbol[], value: string | null, onChange: (symbol: string) => void, className?: string,
}) {
  const t = useT(widgets);
  return (
    <ComboBox className={className} selectedKey={value} menuTrigger="focus" allowsEmptyCollection
      onSelectionChange={(key) => { if (key != null && key !== value) onChange(String(key)); }}>
      <Label>{t('pickerLabel', { n: symbols.length })}</Label>
      <ComboBox.InputGroup>
        <Input placeholder={t('pickerSearch')} className="font-mono" />
        <ComboBox.Trigger />
      </ComboBox.InputGroup>
      <ComboBox.Popover className="max-h-80">
        <ListBox renderEmptyState={() => <EmptyState className="p-3 text-sm text-muted">{t('pickerNone')}</EmptyState>}>
          {symbols.map((s) => (
            <ListBox.Item key={s.symbol} id={s.symbol} textValue={s.symbol}>
              <span className="flex min-w-0 items-center gap-2">
                <ListAvatar name={s.symbol} size="sm" />
                <span className="font-mono font-semibold">{s.symbol}</span>
                {s.exchange ? <span className="text-xs text-muted">{s.exchange}</span> : null}
              </span>
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </ComboBox.Popover>
    </ComboBox>
  );
}
