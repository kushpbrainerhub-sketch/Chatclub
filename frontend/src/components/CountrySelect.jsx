import { Field, Label, Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/react";
import { COUNTRIES, flag } from "../countries.js";

export default function CountrySelect({ label, value, onChange, placeholder, excluded = [], error }) {
  const selected = COUNTRIES.find((country) => country.code === value);

  return (
    <Field className="field grow">
      <Label className="label">{label}</Label>
      <Listbox value={value} onChange={onChange}>
        <ListboxButton aria-invalid={Boolean(error)} className="flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3.5 py-3 text-left text-sm text-[var(--text)] transition hover:border-violet-400/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-400 data-open:border-violet-400">
          <span className={`truncate ${selected ? "" : "text-[var(--muted)]"}`}>
            {selected ? `${flag(selected.code)} ${selected.name}` : placeholder}
          </span>
          <svg className="size-4 shrink-0 text-[var(--muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
        </ListboxButton>
        <ListboxOptions anchor="bottom start" className="z-50 max-h-64 w-[var(--button-width)] overflow-auto rounded-xl border border-[var(--border)] bg-[var(--card)] p-1.5 text-sm text-[var(--text)] shadow-2xl outline-none [--anchor-gap:6px] [--anchor-padding:12px]">
          {COUNTRIES.filter((country) => !excluded.includes(country.code)).map((country) => (
            <ListboxOption key={country.code} value={country.code} className="group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 select-none data-focus:bg-[var(--note-bg)] data-selected:text-[var(--primary)]">
              <span aria-hidden="true">{flag(country.code)}</span>
              <span className="flex-1">{country.name}</span>
              <span className="invisible group-data-selected:visible" aria-hidden="true">✓</span>
            </ListboxOption>
          ))}
          {excluded.length === COUNTRIES.length && <p className="px-3 py-2 text-[var(--muted)]">All countries selected</p>}
        </ListboxOptions>
      </Listbox>
      {error && <small className="error">{error}</small>}
    </Field>
  );
}
