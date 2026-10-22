import type { ReactNode } from "react";
import { formatBytes, type JobResult } from "../api/client";

interface ResultPanelProps {
  result: JobResult;
  /** Optional extra line, e.g. a size comparison. */
  summary?: ReactNode;
  onReset: () => void;
  resetLabel?: string;
}

export default function ResultPanel({
  result,
  summary,
  onReset,
  resetLabel = "Start over",
}: ResultPanelProps) {
  return (
    <div className="result" role="status">
      <p className="alert alert--success">
        Done. <strong>{result.filename}</strong> ({formatBytes(result.size)}) is ready.
      </p>
      {summary && <p className="result__summary">{summary}</p>}
      <div className="result__actions">
        <a className="btn" href={result.download_url} download={result.filename}>
          Download
        </a>
        <button type="button" className="btn btn--secondary" onClick={onReset}>
          {resetLabel}
        </button>
      </div>
    </div>
  );
}
