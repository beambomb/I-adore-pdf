import { OCR_LANGUAGES, toggleLanguage, type OcrLanguage } from "../lib/ocr";

interface LanguageSelectProps {
  value: OcrLanguage[];
  disabled?: boolean;
  onChange: (value: OcrLanguage[]) => void;
}

export default function LanguageSelect({ value, disabled = false, onChange }: LanguageSelectProps) {
  return (
    <fieldset className="field-group" disabled={disabled}>
      <legend>Document language</legend>
      {OCR_LANGUAGES.map((language) => (
        <label key={language.code} className="radio">
          <input
            type="checkbox"
            checked={value.includes(language.code)}
            onChange={() => onChange(toggleLanguage(value, language.code))}
          />{" "}
          {language.label}
        </label>
      ))}
      <p className="hint">Select every language that appears in the document.</p>
    </fieldset>
  );
}
