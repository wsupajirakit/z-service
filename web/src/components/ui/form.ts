// Shared class names for controls (shadcn/ui look), so every page uses the same buttons,
// inputs and labels and colours stay theme tokens. Works on <button>, <a> and <label>.
import { cn } from './cn.ts'

export type ButtonVariant = 'default' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link'
export type ButtonSize = 'sm' | 'md' | 'icon' | 'icon-sm' | 'icon-xs'
/** inline: sized to its content; block: full width, content on the left (lists of links). */
export type ButtonLayout = 'inline' | 'block'

const base = 'items-center gap-2 whitespace-nowrap rounded-md '
  + 'text-sm font-medium transition-colors select-none cursor-pointer '
  + 'disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none '
  + 'aria-disabled:opacity-50'

const variants: Record<ButtonVariant, string> = {
  default: 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90',
  secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  outline: 'border border-input bg-background shadow-sm hover:bg-accent '
    + 'hover:text-accent-foreground',
  ghost: 'hover:bg-accent hover:text-accent-foreground',
  destructive: 'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
  link: 'text-primary underline-offset-4 hover:underline',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4',
  icon: 'size-9',
  'icon-sm': 'size-8',
  'icon-xs': 'size-6',
}

const layouts: Record<ButtonLayout, string> = {
  inline: 'inline-flex justify-center',
  block: 'flex w-full justify-start',
}

/** Each part sets different properties, so the result never needs a class override. */
export function button(variant: ButtonVariant = 'outline', size: ButtonSize = 'md',
  layout: ButtonLayout = 'inline'): string {
  return cn(base, layouts[layout], variants[variant],
    variant === 'link' ? 'h-auto px-0' : sizes[size])
}

export const buttonClass = button('outline')
export const primaryButtonClass = button('default')
export const dangerButtonClass = button('destructive')
export const ghostButtonClass = button('ghost')

const control = 'rounded-md border border-input bg-background text-sm shadow-sm '
  + 'transition-colors placeholder:text-muted-foreground focus-visible:border-ring '
  + 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 '
  + 'disabled:cursor-not-allowed disabled:opacity-50'

export const inputClass = cn(control, 'h-9 min-w-0 px-3')
/** Input with a leading icon (search boxes). */
export const searchInputClass = cn(control, 'h-9 w-full min-w-0 pr-3 pl-8')
export const selectClass = cn(control, 'h-9 min-w-0 px-2')
/** Compact select for toolbars and table footers. */
export const selectSmClass = cn(control, 'h-8 min-w-0 px-2')
export const textareaClass = cn(control, 'min-h-20 px-3 py-2')

/** Label above its control (forms in cards and dialogs). */
export const fieldClass = 'flex flex-col gap-1.5 text-sm font-medium'
/** Label beside its control (checkboxes, compact toolbars). */
export const inlineFieldClass = 'flex items-center gap-2 text-sm'
/** Grid of fields that wraps on small screens. */
export const formGridClass = 'grid gap-4 sm:grid-cols-2'
/** Row of fields and buttons aligned on their bottom edge. */
export const formRowClass = 'flex flex-wrap items-end gap-3'
export const fieldErrorClass = 'text-sm font-normal text-destructive'
export const hintClass = 'text-xs font-normal text-muted-foreground'
