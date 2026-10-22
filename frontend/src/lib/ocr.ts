export type OcrLanguage = "eng" | "ind";

export const OCR_LANGUAGES: { code: OcrLanguage; label: string }[] = [
  { code: "eng", label: "English" },
  { code: "ind", label: "Indonesian" },
];

/** Value sent to the server, e.g. "eng,ind". Keeps the order shown in the UI. */
export function toLanguagesParam(selected: OcrLanguage[]): string {
  return OCR_LANGUAGES.map((l) => l.code)
    .filter((code) => selected.includes(code))
    .join(",");
}

/** Toggle a language on or off, but never allow the selection to become empty. */
export function toggleLanguage(selected: OcrLanguage[], code: OcrLanguage): OcrLanguage[] {
  if (selected.includes(code)) {
    return selected.length === 1 ? selected : selected.filter((c) => c !== code);
  }
  return [...selected, code];
}
