// Joins class names, skipping empty ones. Variants below never set the same property twice,
// so no class-merging library is needed.
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
