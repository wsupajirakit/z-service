import { ComboBox, EmptyState, Input, ListBox } from '@heroui/react';
import { SearchX } from 'lucide-react';
import { useMemo, useState, type Key } from 'react';
import { useT } from '../i18n';
import { widgets } from '../i18n/messages/widgets';

export type AutocompleteOption = string | { [key: string]: string };

export interface AutocompleteProps<T extends AutocompleteOption> {
  value: string;
  onChange: (value: string) => void;
  options: readonly T[];
  placeholder?: string;
  labelKey?: string;
  valueKey?: string;
  onSelectOption?(option: T): void;
}

const optionValue = (opt: AutocompleteOption, valueKey?: string) =>
  typeof opt === 'string' ? opt : String(opt[valueKey ?? ''] ?? '');
const optionLabel = (opt: AutocompleteOption, labelKey?: string) =>
  typeof opt === 'string' ? '' : String(opt[labelKey ?? ''] ?? '');

// Free-text field with a filtered option list. While open it shows the search text (cleared
// on focus, so every option is listed); closed it shows `value`. Typed text is reported
// upper-cased through onChange; picking an option reports its value and calls onSelectOption.
export function Autocomplete<T extends AutocompleteOption>({
  value, onChange, options, placeholder, labelKey, valueKey, onSelectOption,
}: AutocompleteProps<T>) {
  const t = useT(widgets);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const items = useMemo(() => {
    const needle = search.toLowerCase();
    return options
      .map((opt, idx) => ({ id: idx, opt, value: optionValue(opt, valueKey), label: optionLabel(opt, labelKey) }))
      .filter((it) => `${it.value} ${it.label}`.toLowerCase().includes(needle));
  }, [options, search, valueKey, labelKey]);

  const selectedKey = useMemo(() => {
    const idx = options.findIndex((opt) => optionValue(opt, valueKey) === value);
    return idx >= 0 ? idx : null;
  }, [options, value, valueKey]);

  const select = (key: Key | null) => {
    if (key === null) return;
    const opt = options[Number(key)];
    if (opt === undefined) return;
    onChange(optionValue(opt, valueKey));
    setSearch('');
    onSelectOption?.(opt);
  };

  return (
    <ComboBox
      aria-label={placeholder ?? t('acPlaceholder')}
      fullWidth
      allowsCustomValue
      allowsEmptyCollection
      menuTrigger="focus"
      items={items}
      defaultFilter={() => true}
      inputValue={open ? search : value}
      onInputChange={(text) => {
        setSearch(text);
        onChange(text.toUpperCase());
      }}
      selectedKey={selectedKey}
      onSelectionChange={select}
      onOpenChange={(isOpen, trigger) => {
        setOpen(isOpen);
        if (isOpen && trigger !== 'input') setSearch('');
      }}
    >
      <ComboBox.InputGroup>
        <Input placeholder={placeholder ?? t('acPlaceholder')} />
        <ComboBox.Trigger aria-label={t('acToggle')} />
      </ComboBox.InputGroup>
      <ComboBox.Popover>
        <ListBox
          className="max-h-64 overflow-y-auto"
          renderEmptyState={() => (
            <EmptyState className="flex items-center justify-center gap-2 py-3 text-sm text-muted">
              <SearchX className="size-4" />
              {t('acNoMatch')}
            </EmptyState>
          )}
        >
          {(it: (typeof items)[number]) => (
            <ListBox.Item id={it.id} textValue={it.value}>
              <div className="flex min-w-0 flex-col sm:flex-row sm:items-baseline sm:gap-2">
                <span className="font-semibold">{it.value}</span>
                {it.label ? <span className="truncate text-xs text-muted">{it.label}</span> : null}
              </div>
              <ListBox.ItemIndicator />
            </ListBox.Item>
          )}
        </ListBox>
      </ComboBox.Popover>
    </ComboBox>
  );
}
