import { useEffect, useState } from "react";
import { ApiError, postForm } from "../api/client";

export type ScanMode = "bw" | "grayscale" | "color";

interface PreviewResponse {
  image: string;
  cropped: boolean;
}

interface ScanPreviewProps {
  file: File;
  mode: ScanMode;
  autoCrop: boolean;
}

/** Shows the original photo next to the processed scan, refreshed when options change. */
export default function ScanPreview({ file, mode, autoCrop }: ScanPreviewProps) {
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setOriginalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    const controller = new AbortController();
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("mode", mode);
    form.append("auto_crop", String(autoCrop));
    setLoading(true);
    setError(null);

    postForm<PreviewResponse>("/api/scan/preview", form, undefined, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) setPreview(response);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setPreview(null);
        setError(err instanceof ApiError ? err.message : "Could not create a preview.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [file, mode, autoCrop]);

  return (
    <div className="scan-preview">
      <figure className="scan-preview__pane">
        <figcaption>Original</figcaption>
        {originalUrl && <img src={originalUrl} alt={`Original photo ${file.name}`} />}
      </figure>
      <figure className="scan-preview__pane">
        <figcaption>Scan result</figcaption>
        {loading && <p className="hint">Processing preview...</p>}
        {!loading && preview && <img src={preview.image} alt={`Scanned preview of ${file.name}`} />}
        {!loading && error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
        {!loading && preview && autoCrop && !preview.cropped && (
          <p className="hint">Could not find the page edges, so the whole photo is used.</p>
        )}
      </figure>
    </div>
  );
}
