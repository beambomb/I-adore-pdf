import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, formatBytes, postForm } from "./client";

class FakeXhr {
  static last: FakeXhr;
  status = 0;
  responseText = "";
  responseType = "";
  upload: { onprogress?: (e: unknown) => void } = {};
  onload?: () => void;
  onerror?: () => void;
  onabort?: () => void;
  open = vi.fn();
  abort = vi.fn(() => this.onabort?.());
  send = vi.fn();
  constructor() {
    FakeXhr.last = this;
  }
}

afterEach(() => vi.unstubAllGlobals());

function setup() {
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
}

describe("postForm", () => {
  it("resolves with parsed JSON and reports progress", async () => {
    setup();
    const onProgress = vi.fn();
    const promise = postForm<{ ok: boolean }>("/api/x", new FormData(), onProgress);
    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 });
    FakeXhr.last.status = 200;
    FakeXhr.last.responseText = JSON.stringify({ ok: true });
    FakeXhr.last.onload?.();
    await expect(promise).resolves.toEqual({ ok: true });
    expect(onProgress).toHaveBeenCalledWith(0.5);
  });

  it("rejects with the server's detail message", async () => {
    setup();
    const promise = postForm("/api/x", new FormData());
    FakeXhr.last.status = 415;
    FakeXhr.last.responseText = JSON.stringify({ detail: "'a.pdf' is not a supported file type." });
    FakeXhr.last.onload?.();
    await expect(promise).rejects.toMatchObject({
      name: "ApiError",
      status: 415,
      message: "'a.pdf' is not a supported file type.",
    });
  });

  it("rejects with a friendly message on network errors", async () => {
    setup();
    const promise = postForm("/api/x", new FormData());
    FakeXhr.last.onerror?.();
    const error = await promise.catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toMatch(/Could not reach the server/);
  });

  it("aborts when the signal fires", async () => {
    setup();
    const controller = new AbortController();
    const promise = postForm("/api/x", new FormData(), undefined, controller.signal);
    controller.abort();
    await expect(promise).rejects.toThrow("Upload cancelled.");
  });
});

describe("formatBytes", () => {
  it("formats sizes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
