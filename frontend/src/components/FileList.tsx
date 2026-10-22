import { formatBytes } from "../api/client";

export interface QueuedFile {
  id: number;
  file: File;
}

interface FileListProps {
  items: QueuedFile[];
  disabled?: boolean;
  onMove: (from: number, to: number) => void;
  onRemove: (index: number) => void;
}

export default function FileList({ items, disabled = false, onMove, onRemove }: FileListProps) {
  if (items.length === 0) return null;
  return (
    <ol className="file-list" aria-label="Selected files">
      {items.map((item, index) => (
        <li key={item.id} className="file-list__item">
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
