import { useState } from "react";
import { ApiError, formatBytes, postForm, type JobResult } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import LanguageSelect from "../components/LanguageSelect";
import ResultPanel from "../components/ResultPanel";
import ToolLayout from "../components/ToolLayout";
import { toLanguagesParam, type OcrLanguage } from "../lib/ocr";

export default function OcrPage() {
  const [file, setFile] = useState<File | null>(null);
  const [languages, setLanguages] = useState<OcrLanguage[]>(["eng"]);
  const [skipText, setSkipText] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);

  async function recognize() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("languages", toLanguagesParam(languages));
    form.append("skip_text", String(skipText));
    try {
      setResult(await postForm<JobResult>("/api/ocr", form, setProgress));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
  }

  return (
    <ToolLayout
      title="OCR PDF"
      description="Make a scanned PDF searchable so you can select and copy its text."
    >
      {result ? (
        <ResultPanel result={result} onReset={reset} resetLabel="Process another file" />
      ) : (
        <>
          {!file ? (
            <FileDropzone
              accept={["application/pdf", ".pdf"]}
              disabled={busy}
              label="Select a PDF file"
              onFiles={(files) => {
                setFile(files[0]);
                setError(null);
              }}
            />
          ) : (
            <p className="file-summary">
              <strong>{file.name}</strong> ({formatBytes(file.size)}){" "}
              <button type="button" className="btn btn--secondary btn--small" disabled={busy} onClick={reset}>
                Change file
              </button>
            </p>
          )}

          {file && (
            <>
              <LanguageSelect value={languages} disabled={busy} onChange={setLanguages} />
              <div className="field-group">
                <label className="radio">
                  <input
                    type="checkbox"
                    checked={skipText}
                    disabled={busy}
                    onChange={(event) => setSkipText(event.target.checked)}
                  />{" "}
                  Skip pages that already contain text
                </label>
              </div>
            </>
          )}

          {busy && (
            <>
              <progress className="progress" value={progress} max={1} aria-label="Upload progress" />
              {progress >= 1 && (
                <p className="hint" role="status">
                  Recognizing text. This can take a minute or more for long documents.
                </p>
              )}
            </>
          )}
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button type="button" className="btn" disabled={busy || !file} onClick={recognize}>
              {busy ? "Recognizing..." : "Run OCR"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
