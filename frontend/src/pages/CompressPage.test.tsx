import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import CompressPage from "./CompressPage";

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

const MB = 1024 * 1024;
const compressed = {
  job_id: "4".repeat(32),
  filename: "doc-compressed.pdf",
  size: MB,
  media_type: "application/pdf",
  download_url: "/api/download/" + "4".repeat(32),
  original_size: 5 * MB,
  compressed_size: MB,
  saved_percent: 80,
  already_optimal: false,
};

const pdf = () => new File(["%PDF-1.7"], "doc.pdf", { type: "application/pdf" });

beforeEach(() => {
  calls = [];
  handler = () => Promise.resolve(compressed);
});

describe("CompressPage", () => {
  it("needs a file before compressing and defaults to the recommended level", async () => {
    render(<CompressPage />);
    expect(screen.getByRole("button", { name: "Compress PDF" })).toBeDisabled();
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    expect(screen.getByRole("button", { name: "Compress PDF" })).toBeEnabled();
    expect(screen.getByLabelText(/Recommended compression/)).toBeChecked();
  });

  it("sends the chosen level and shows before and after sizes", async () => {
    render(<CompressPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByLabelText(/Extreme compression/));
    await userEvent.click(screen.getByRole("button", { name: "Compress PDF" }));

    expect(await screen.findByText("5.0 MB → 1.0 MB (-80%)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      compressed.download_url,
    );
    const [url, form] = calls[0];
    expect(url).toBe("/api/compress");
    expect(form.get("level")).toBe("high");
    expect((form.get("file") as File).name).toBe("doc.pdf");
  });

  it("tells the user when the file could not be made smaller", async () => {
    handler = () =>
      Promise.resolve({ ...compressed, compressed_size: 5 * MB, saved_percent: 0, already_optimal: true });
    render(<CompressPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Compress PDF" }));
    expect(await screen.findByText(/could not be made smaller/)).toBeInTheDocument();
  });

  it("shows server errors and keeps the selected file", async () => {
    handler = () =>
      Promise.reject(new ApiError("Compression is unavailable: Ghostscript is not installed.", 503));
    render(<CompressPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Compress PDF" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Ghostscript"));
    expect(screen.getByText("doc.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compress PDF" })).toBeEnabled();
  });
});
