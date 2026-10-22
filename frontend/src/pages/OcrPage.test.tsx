import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import OcrPage from "./OcrPage";

// Plain function mock (not vi.fn) so rejected promises are not reported as unhandled.
let handler: (url: string, form: FormData) => Promise<unknown> = () => Promise.resolve({});
let calls: [string, FormData][] = [];

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    postForm: (url: string, form: FormData) => {
      calls.push([url, form]);
      return handler(url, form);
    },
  };
});

const job = {
  job_id: "6".repeat(32),
  filename: "doc-ocr.pdf",
  size: 4096,
  media_type: "application/pdf",
  download_url: "/api/download/" + "6".repeat(32),
};

const pdf = () => new File(["%PDF-1.7"], "doc.pdf", { type: "application/pdf" });

beforeEach(() => {
  calls = [];
  handler = () => Promise.resolve(job);
});

describe("OcrPage", () => {
  it("needs a file and defaults to English with skip-text on", async () => {
    render(<OcrPage />);
    expect(screen.getByRole("button", { name: "Run OCR" })).toBeDisabled();
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    expect(screen.getByRole("button", { name: "Run OCR" })).toBeEnabled();
    expect(screen.getByLabelText("English")).toBeChecked();
    expect(screen.getByLabelText("Indonesian")).not.toBeChecked();
    expect(screen.getByLabelText(/Skip pages that already contain text/)).toBeChecked();
  });

  it("keeps at least one language selected", async () => {
    render(<OcrPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByLabelText("English"));
    expect(screen.getByLabelText("English")).toBeChecked();
  });

  it("sends the chosen languages and options, then offers the download", async () => {
    render(<OcrPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByLabelText("Indonesian"));
    await userEvent.click(screen.getByLabelText(/Skip pages that already contain text/));
    await userEvent.click(screen.getByRole("button", { name: "Run OCR" }));

    expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      job.download_url,
    );
    const [url, form] = calls[0];
    expect(url).toBe("/api/ocr");
    expect(form.get("languages")).toBe("eng,ind");
    expect(form.get("skip_text")).toBe("false");
    expect((form.get("file") as File).name).toBe("doc.pdf");
  });

  it("shows an error when OCR is unavailable", async () => {
    handler = () =>
      Promise.reject(new ApiError("OCR is unavailable: Tesseract is not installed.", 503));
    render(<OcrPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Run OCR" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Tesseract"));
    expect(screen.getByRole("button", { name: "Run OCR" })).toBeEnabled();
  });
});
