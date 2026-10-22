import { useId, useRef, useState, type DragEvent } from "react";

export interface FileDropzoneProps {
  /** MIME types or extensions, e.g. ["application/pdf", ".pdf"]. */
  accept: string[];
  multiple?: boolean;
  maxFileBytes?: number;
  label?: string;
  hint?: string;
  disabled?: boolean;
  onFiles: (files: File[]) => void;
}

export function matchesAccept(file: File, accept: string[]): boolean {
  const name = file.name.toLowerCase();
  return accept.some((token) =>
    token.startsWith(".") ? name.endsWith(token.toLowerCase()) : file.type === token,
  );
}

function formatMb(bytes: number): string {
  return `${Math.round(bytes / (1024 * 1024))} MB`;
}

export default function FileDropzone({
  accept,
  multiple = false,
  maxFileBytes,
  label = "Select files",
  hint,
  disabled = false,
  onFiles,
}: FileDropzoneProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  function handle(list: FileList | null) {
    if (!list || list.length === 0) return;
    const accepted: File[] = [];
    const rejected: string[] = [];
    for (const file of Array.from(list)) {
      if (!matchesAccept(file, accept)) {
        rejected.push(`${file.name}: unsupported file type.`);
      } else if (maxFileBytes !== undefined && file.size > maxFileBytes) {
        rejected.push(`${file.name}: larger than ${formatMb(maxFileBytes)}.`);
      } else {
        accepted.push(file);
      }
    }
    const usable = multiple ? accepted : accepted.slice(0, 1);
    if (!multiple && accepted.length > 1) {
      rejected.push("Only one file can be selected here.");
    }
    setErrors(rejected);
    if (usable.length > 0) onFiles(usable);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (!disabled) handle(event.dataTransfer.files);
  }

  return (
    <div>
      <div
        className={`dropzone${dragging ? " dropzone--active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <button
          type="button"
          className="btn"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          {label}
        </button>
        <p className="dropzone__hint">{hint ?? "or drop files here"}</p>
        <label htmlFor={inputId} className="visually-hidden">
          Choose files
        </label>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          className="visually-hidden"
          accept={accept.join(",")}
          multiple={multiple}
          disabled={disabled}
          onChange={(event) => {
            handle(event.target.files);
            event.target.value = "";
          }}
        />
      </div>
      {errors.length > 0 && (
        <ul className="alert" role="alert">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
