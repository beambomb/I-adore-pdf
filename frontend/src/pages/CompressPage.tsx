import { useState } from "react";
import { ApiError, formatBytes, postForm } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import ResultPanel from "../components/ResultPanel";
import ToolLayout from "../components/ToolLayout";
import { LEVELS, describeSavings, type CompressResult, type CompressionLevel } from "../lib/compression";

export default function CompressPage() {
  const [file, setFile] = useState<File | null>(null);
  const [level, setLevel] = useState<CompressionLevel>("medium");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompressResult | null>(null);

  async function compress() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("level", level);
    try {
      setResult(await postForm<CompressResult>("/api/compress", form, setProgress));
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
      title="Compress PDF"
      description="Reduce the file size of a PDF while keeping it readable."
    >
      {result ? (
        <ResultPanel
          result={result}
          summary={describeSavings(result)}
          onReset={reset}
          resetLabel="Compress another file"
        />
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
            <fieldset className="field-group" disabled={busy}>
              <legend>Compression level</legend>
              {LEVELS.map((option) => (
                <label key={option.value} className="radio">
                  <input
                    type="radio"
                    name="level"
                    checked={level === option.value}
                    onChange={() => setLevel(option.value)}
                  />{" "}
                  <strong>{option.label}</strong>
                  <span className="hint hint--inline"> {option.description}</span>
                </label>
              ))}
            </fieldset>
          )}

          {busy && <progress className="progress" value={progress} max={1} aria-label="Upload progress" />}
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button type="button" className="btn" disabled={busy || !file} onClick={compress}>
              {busy ? "Compressing..." : "Compress PDF"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
