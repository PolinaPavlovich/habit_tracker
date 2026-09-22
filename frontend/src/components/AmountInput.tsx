interface AmountInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  onSubmit?: () => void
}

/**
 * A text input for a decimal amount.
 *
 * Deliberately `type="text"` with `inputMode="decimal"` rather than
 * `type="number"`: a number input hands back a coerced `valueAsNumber` and, in
 * several browsers, silently rejects or reformats the comma decimal separator
 * many locales type. The raw string is what we want, and `lib/decimal`
 * validates it.
 */
export function AmountInput({ value, onChange, placeholder, onSubmit }: AmountInputProps) {
  return (
    <input
      type="text"
      inputMode="decimal"
      autoComplete="off"
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' && onSubmit) onSubmit()
      }}
    />
  )
}
