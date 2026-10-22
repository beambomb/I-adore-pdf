import { useState } from "react";
import { ApiError, formatBytes, postForm, type JobResult } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import ResultPanel from "../components/ResultPanel";
import ToolLayout from "../components/ToolLayout";
import { validateRanges } from "../lib/ranges";

type Mode = "ranges" | "all";

interface SplitInfo {
  filename: string;
  pages: number;
}

export default function SplitPage() {
  const [file, setFile] = useState<File | null>(null);
  const [pages, setPages] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>("ranges");
  const [ranges, setRanges] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);

  const rangeError = mode === "ranges" && pages !== null && ranges !== "" ? validateRanges(ranges, pages) : null;
  const canSplit =
    file !== null &&
    pages !== null &&
    !busy &&
    (mode === "all" || (ranges.trim() !== "" && validateRanges(ranges, pages) === null));

  async function chooseFile(files: File[]) {
    const chosen = files[0];
    setFile(chosen);
    setPages(null);
    setError(null);
    setBusy(true);
    const form = new FormData();
    form.append("file", chosen, chosen.name);
    try {
      const info = await postForm<SplitInfo>("/api/split/info", form);
      setPages(info.pages);
    } catch (err) {
      setFile(null);
      setError(err instanceof ApiError ? err.message : "Could not read this PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function split() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("mode", mode);
    if (mode === "ranges") form.append("ranges", ranges);
    try {
      setResult(await postForm<JobResult>("/api/split", form, setProgress));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setFile(null);
    setPages(null);
    setRanges("");
    setResult(null);
    setError(null);
    setProgress(0);
  }

  return (
    <ToolLayout
      title="Split PDF"
      description="Extract specific pages into a new PDF, or save every page as its own file."
    >
      {result ? (
        <ResultPanel result={result} onReset={reset} resetLabel="Split another file" />
      ) : (
        <>
          {!file ? (
            <FileDropzone
              accept={["application/pdf", ".pdf"]}
              disabled={busy}
              label="Select a PDF file"
              onFiles={chooseFile}
            />
          ) : (
            <p className="file-summary">
              <strong>{file.name}</strong> ({formatBytes(file.size)}
              {pages !== null && `, ${pages} page${pages === 1 ? "" : "s"}`}){" "}
              <button type="button" className="btn btn--secondary btn--small" disabled={busy} onClick={reset}>
                Change file
              </button>
            </p>
          )}

          {file && pages !== null && (
            <>
              <fieldset className="field-group" disabled={busy}>
                <legend>Split mode</legend>
                <label className="radio">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === "ranges"}
                    onChange={() => setMode("ranges")}
                  />{" "}
                  Extract page ranges
                </label>
                <label className="radio">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === "all"}
                    onChange={() => setMode("all")}
                  />{" "}
                  Save every page as a separate PDF (ZIP)
                </label>
              </fieldset>

              {mode === "ranges" && (
                <div className="field-group">
                  <label htmlFor="ranges">Pages to extract</label>
                  <input
                    id="ranges"
                    type="text"
                    className="text-input"
                    value={ranges}
                    placeholder="e.g. 1-3,5,8-"
                    aria-invalid={rangeError !== null}
                    aria-describedby="ranges-help"
                    disabled={busy}
                    onChange={(event) => setRanges(event.target.value)}
                  />
                  <p id="ranges-help" className={rangeError ? "field-error" : "hint"}>
                    {rangeError ?? `Use commas and dashes. "8-" means page 8 to the end. This file has ${pages} page${pages === 1 ? "" : "s"}.`}
                  </p>
                </div>
              )}
            </>
          )}

          {busy && <progress className="progress" value={progress} max={1} aria-label="Upload progress" />}
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button type="button" className="btn" disabled={!canSplit} onClick={split}>
              {busy && pages !== null ? "Splitting..." : "Split PDF"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
