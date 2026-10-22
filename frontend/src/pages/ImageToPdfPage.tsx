import { useState } from "react";
import { ApiError, postForm, type JobResult } from "../api/client";
import FileDropzone from "../components/FileDropzone";
import FileList from "../components/FileList";
import ResultPanel from "../components/ResultPanel";
import ToolLayout from "../components/ToolLayout";
import { useFileQueue } from "../hooks/useFileQueue";

type PageSize = "fit" | "a4";
type Orientation = "auto" | "portrait" | "landscape";

const IMAGE_ACCEPT = ["image/jpeg", "image/png", "image/webp", ".jpg", ".jpeg", ".png", ".webp"];

export default function ImageToPdfPage() {
  const queue = useFileQueue();
  const { items } = queue;
  const [pageSize, setPageSize] = useState<PageSize>("fit");
  const [orientation, setOrientation] = useState<Orientation>("auto");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);

  async function convert() {
    setBusy(true);
    setError(null);
    setProgress(0);
    const form = new FormData();
    items.forEach((item) => form.append("files", item.file, item.file.name));
    form.append("page_size", pageSize);
    form.append("orientation", orientation);
    try {
      setResult(await postForm<JobResult>("/api/image-to-pdf", form, setProgress));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    queue.clear();
    setResult(null);
    setError(null);
    setProgress(0);
  }

  return (
    <ToolLayout
      title="Image to PDF"
      description="Turn JPG, PNG or WEBP images into a PDF. Each image becomes one page, in the order shown."
    >
      {result ? (
        <ResultPanel result={result} onReset={reset} resetLabel="Convert more images" />
      ) : (
        <>
          <FileDropzone
            accept={IMAGE_ACCEPT}
            multiple
            disabled={busy}
            label="Select images"
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
              <div className="field-group">
                <label htmlFor="page-size">Page size</label>
                <select
                  id="page-size"
                  className="text-input"
                  value={pageSize}
                  disabled={busy}
                  onChange={(event) => setPageSize(event.target.value as PageSize)}
                >
                  <option value="fit">Same as image</option>
                  <option value="a4">A4</option>
                </select>
              </div>
              {pageSize === "a4" && (
                <div className="field-group">
                  <label htmlFor="orientation">Orientation</label>
                  <select
                    id="orientation"
                    className="text-input"
                    value={orientation}
                    disabled={busy}
                    onChange={(event) => setOrientation(event.target.value as Orientation)}
                  >
                    <option value="auto">Match each image</option>
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                  </select>
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
            <button
              type="button"
              className="btn"
              disabled={busy || items.length === 0}
              onClick={convert}
            >
              {busy ? "Converting..." : "Convert to PDF"}
            </button>
          </div>
        </>
      )}
    </ToolLayout>
  );
}
