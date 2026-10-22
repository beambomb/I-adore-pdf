import { useEffect, useState } from "react";
import { formatBytes } from "../api/client";

export interface QueuedFile {
  id: number;
  file: File;
}

interface FileListProps {
  items: QueuedFile[];
  disabled?: boolean;
  /** Show a small preview next to image files. */
  thumbnails?: boolean;
  onMove: (from: number, to: number) => void;
  onRemove: (index: number) => void;
}

function Thumbnail({ file }: { file: File }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  // Decorative: the file name is always shown next to it.
  return url ? <img className="file-list__thumb" src={url} alt="" /> : null;
}

export default function FileList({
  items,
  disabled = false,
  thumbnails = false,
  onMove,
  onRemove,
}: FileListProps) {
  if (items.length === 0) return null;
  return (
    <ol className="file-list" aria-label="Selected files">
      {items.map((item, index) => (
        <li key={item.id} className="file-list__item">
          {thumbnails && <Thumbnail file={item.file} />}
          <span className="file-list__name">{item.file.name}</span>
          <span className="file-list__size">{formatBytes(item.file.size)}</span>
          <span className="file-list__actions">
            <button
              type="button"
              className="btn btn--secondary btn--small"
              aria-label={`Move ${item.file.name} up`}
              disabled={disabled || index === 0}
              onClick={() => onMove(index, index - 1)}
            >
              Up
            </button>
            <button
              type="button"
              className="btn btn--secondary btn--small"
              aria-label={`Move ${item.file.name} down`}
              disabled={disabled || index === items.length - 1}
              onClick={() => onMove(index, index + 1)}
            >
              Down
            </button>
            <button
              type="button"
              className="btn btn--secondary btn--small"
              aria-label={`Remove ${item.file.name}`}
              disabled={disabled}
              onClick={() => onRemove(index)}
            >
              Remove
            </button>
          </span>
        </li>
      ))}
    </ol>
  );
}
