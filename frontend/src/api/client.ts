export interface JobResult {
  job_id: string;
  filename: string;
  size: number;
  media_type: string;
  download_url: string;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      const first = parsed.detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  } catch {
    // Not JSON; fall through to the generic message.
  }
  if (status === 0) return "Could not reach the server. Is the backend running?";
  if (status === 413) return "The upload is too large.";
  return `Request failed (${status}).`;
}

/**
 * POST multipart form data and parse the JSON response.
 * Uses XMLHttpRequest because fetch cannot report upload progress.
 */
export function postForm<T>(
  url: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.responseType = "text";

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          reject(new ApiError("The server sent an unexpected response.", xhr.status));
        }
      } else {
        reject(new ApiError(errorMessage(xhr.status, xhr.responseText), xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError(errorMessage(0, ""), 0));
    xhr.onabort = () => reject(new ApiError("Upload cancelled.", 0));

    signal?.addEventListener("abort", () => xhr.abort());
    xhr.send(form);
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
