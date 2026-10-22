import { useRef, useState } from "react";
import { ApiError, postForm, type JobResult } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import FileList, { type QueuedFile } from "../components/FileList";
import ResultPanel from "../components/ResultPanel";
import ToolLayout from "../components/ToolLayout";
import { moveItem, removeAt } from "../lib/reorder";

export default function MergePage() {
  const nextId = useRef(1);
  const [items, setItems] = useState<QueuedFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);

  function addFiles(files: File[]) {
    setItems((current) => [...current, ...files.map((file) => ({ id: nextId.current++, file }))]);
    setError(null);
  }

  async function merge() {
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    items.forEach((item) => form.append("files", item.file, item.file.name));
    try {
      setResult(await postForm<JobResult>("/api/merge", form, setProgress));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setItems([]);
    setResult(null);
    setError(null);
    setProgress(0);
  }

  return (
    <ToolLayout
      title="Merge PDF"
      description="Combine several PDF files into one. Files are merged in the order shown below."
    >
      {result ? (
        <ResultPanel result={result} onReset={reset} resetLabel="Merge more files" />
      ) : (
        <>
          <FileDropzone
            accept={["application/pdf", ".pdf"]}
            multiple
            disabled={busy}
            label="Select PDF files"
            onFiles={addFiles}
          />
          <FileList
            items={items}
            disabled={busy}
            onMove={(from, to) => setItems((current) => moveItem(current, from, to))}
            onRemove={(index) => setItems((current) => removeAt(current, index))}
          />
          {items.length === 1 && <p className="hint">Add at least one more PDF to merge.</p>}
          {busy && <progress className="progress" value={progress} max={1} aria-label="Upload progress" />}
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button
              type="button"
              className="btn"
              disabled={busy || items.length < 2}
              onClick={merge}
            >
              {busy ? "Merging..." : "Merge PDF"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
