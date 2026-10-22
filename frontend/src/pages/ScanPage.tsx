import { useState } from "react";
import { ApiError, postForm, type JobResult } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import FileList from "../components/FileList";
import ResultPanel from "../components/ResultPanel";
import ScanPreview, { type ScanMode } from "../components/ScanPreview";
import ToolLayout from "../components/ToolLayout";
import { useFileQueue } from "../hooks/useFileQueue";

const IMAGE_ACCEPT = ["image/jpeg", "image/png", "image/webp", ".jpg", ".jpeg", ".png", ".webp"];

const MODES: { value: ScanMode; label: string }[] = [
  { value: "bw", label: "Black and white" },
  { value: "grayscale", label: "Grayscale" },
  { value: "color", label: "Color" },
];

export default function ScanPage() {
  const queue = useFileQueue();
  const { items } = queue;
  const [mode, setMode] = useState<ScanMode>("bw");
  const [autoCrop, setAutoCrop] = useState(true);
  const [previewId, setPreviewId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);

  // Preview the chosen photo, or the first one if the chosen photo was removed.
  const previewItem = items.find((item) => item.id === previewId) ?? items[0];

  async function scan() {
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    items.forEach((item) => form.append("files", item.file, item.file.name));
    form.append("mode", mode);
    form.append("auto_crop", String(autoCrop));
    try {
      setResult(await postForm<JobResult>("/api/scan", form, setProgress));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    queue.clear();
    setPreviewId(null);
    setResult(null);
    setError(null);
    setProgress(0);
  }

  return (
    <ToolLayout
      title="Scan document"
      description="Turn photos of documents into clean, flat PDF pages. Photos are added to the PDF in the order shown."
    >
      {result ? (
        <ResultPanel result={result} onReset={reset} resetLabel="Scan more documents" />
      ) : (
        <>
          <FileDropzone
            accept={IMAGE_ACCEPT}
            multiple
            disabled={busy}
            label="Select photos"
            onFiles={(files) => {
              queue.add(files);
              setError(null);
            }}
          />
          <FileList
            items={items}
            thumbnails
            disabled={busy}
            onMove={queue.move}
            onRemove={queue.remove}
          />

          {items.length > 0 && (
            <>
              <fieldset className="field-group" disabled={busy}>
                <legend>Color mode</legend>
                {MODES.map((option) => (
                  <label key={option.value} className="radio">
                    <input
                      type="radio"
                      name="mode"
                      checked={mode === option.value}
                      onChange={() => setMode(option.value)}
                    />{" "}
                    {option.label}
                  </label>
                ))}
              </fieldset>

              <div className="field-group">
                <label className="radio">
                  <input
                    type="checkbox"
                    checked={autoCrop}
                    disabled={busy}
                    onChange={(event) => setAutoCrop(event.target.checked)}
                  />{" "}
                  Detect page edges, crop and straighten
                </label>
              </div>

              {items.length > 1 && previewItem && (
                <div className="field-group">
                  <label htmlFor="preview-file">Preview photo</label>
                  <select
                    id="preview-file"
                    className="text-input"
                    value={previewItem.id}
                    onChange={(event) => setPreviewId(Number(event.target.value))}
                  >
                    {items.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.file.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {previewItem && (
                <ScanPreview key={previewItem.id} file={previewItem.file} mode={mode} autoCrop={autoCrop} />
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
            <button type="button" className="btn" disabled={busy || items.length === 0} onClick={scan}>
              {busy ? "Scanning..." : "Scan to PDF"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
