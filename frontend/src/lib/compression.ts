import { formatBytes, type JobResult } from "../api/client";

export type CompressionLevel = "low" | "medium" | "high";

export interface CompressResult extends JobResult {
  original_size: number;
  compressed_size: number;
  saved_percent: number;
  already_optimal: boolean;
}

export const LEVELS: { value: CompressionLevel; label: string; description: string }[] = [
  { value: "low", label: "Low compression", description: "Best quality, smaller saving. Good for printing." },
  { value: "medium", label: "Recommended compression", description: "Good quality and a good saving. Good for most files." },
  { value: "high", label: "Extreme compression", description: "Smallest file, lower image quality. Good for sharing on screen." },
];

/** One-line description of what compression achieved, e.g. "5.2 MB → 1.1 MB (-79%)". */
export function describeSavings(result: CompressResult): string {
  if (result.already_optimal) {
    return `${formatBytes(result.original_size)}: this file could not be made smaller at this level, so the original was kept. Try a stronger level.`;
  }
  const saved = Number.isInteger(result.saved_percent)
    ? result.saved_percent.toString()
    : result.saved_percent.toFixed(1);
  return `${formatBytes(result.original_size)} → ${formatBytes(result.compressed_size)} (-${saved}%)`;
}
