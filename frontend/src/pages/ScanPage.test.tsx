import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import ScanPage from "./ScanPage";

// Plain function mock (not vi.fn) so rejected promises are not reported as unhandled.
type Call = { url: string; form: FormData };
let handler: (call: Call) => Promise<unknown> = () => Promise.resolve({});
let calls: Call[] = [];

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    postForm: (url: string, form: FormData) => {
      const call = { url, form };
      calls.push(call);
      return handler(call);
    },
  };
});

const job = {
  job_id: "5".repeat(32),
  filename: "scan.pdf",
  size: 2048,
  media_type: "application/pdf",
  download_url: "/api/download/" + "5".repeat(32),
};

const photo = (name: string) => new File(["img"], name, { type: "image/jpeg" });
const previews = () => calls.filter((c) => c.url === "/api/scan/preview");

beforeEach(() => {
  calls = [];
  handler = ({ url }) =>
    Promise.resolve(url === "/api/scan/preview" ? { image: "data:image/jpeg;base64,AAAA", cropped: true } : job);
  URL.createObjectURL = vi.fn(() => "blob:mock");
  URL.revokeObjectURL = vi.fn();
});

describe("ScanPage", () => {
  it("needs a photo before scanning", () => {
    render(<ScanPage />);
    expect(screen.getByRole("button", { name: "Scan to PDF" })).toBeDisabled();
  });

  it("shows original and scanned preview with black and white by default", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    expect(await screen.findByAltText("Scanned preview of a.jpg")).toHaveAttribute(
      "src",
      "data:image/jpeg;base64,AAAA",
    );
    expect(screen.getByAltText("Original photo a.jpg")).toBeInTheDocument();
    expect(screen.getByLabelText("Black and white")).toBeChecked();
    expect(previews()[0].form.get("mode")).toBe("bw");
    expect(previews()[0].form.get("auto_crop")).toBe("true");
  });

  it("refreshes the preview when the mode or auto-crop changes", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    await screen.findByAltText("Scanned preview of a.jpg");

    await userEvent.click(screen.getByLabelText("Color"));
    await waitFor(() => expect(previews().at(-1)!.form.get("mode")).toBe("color"));

    await userEvent.click(screen.getByLabelText(/Detect page edges/));
    await waitFor(() => expect(previews().at(-1)!.form.get("auto_crop")).toBe("false"));
  });

  it("warns when the page edges were not found", async () => {
    handler = () => Promise.resolve({ image: "data:image/jpeg;base64,AAAA", cropped: false });
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    expect(await screen.findByText(/Could not find the page edges/)).toBeInTheDocument();
  });

  it("lets the user choose which photo to preview", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), [photo("a.jpg"), photo("b.jpg")]);
    await screen.findByAltText("Scanned preview of a.jpg");
    await userEvent.selectOptions(screen.getByLabelText("Preview photo"), "b.jpg");
    expect(await screen.findByAltText("Scanned preview of b.jpg")).toBeInTheDocument();
  });

  it("sends all photos in order with the options and shows the download", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), [photo("a.jpg"), photo("b.jpg")]);
    await userEvent.click(screen.getByRole("button", { name: "Move b.jpg up" }));
    await userEvent.click(screen.getByLabelText("Grayscale"));
    await userEvent.click(screen.getByRole("button", { name: "Scan to PDF" }));

    expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute("href", job.download_url);
    const scan = calls.find((c) => c.url === "/api/scan")!;
    expect(scan.form.getAll("files").map((f) => (f as File).name)).toEqual(["b.jpg", "a.jpg"]);
    expect(scan.form.get("mode")).toBe("grayscale");
    expect(scan.form.get("auto_crop")).toBe("true");
  });

  it("does not ask for OCR by default", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    expect(screen.queryByLabelText("Indonesian")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Scan to PDF" }));
    await screen.findByRole("link", { name: "Download" });
    const scan = calls.find((c) => c.url === "/api/scan")!;
    expect(scan.form.get("ocr")).toBe("false");
    expect(scan.form.has("languages")).toBe(false);
  });

  it("sends OCR options when 'Make text searchable' is enabled", async () => {
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    await userEvent.click(screen.getByLabelText(/Make text searchable/));
    await userEvent.click(screen.getByLabelText("Indonesian"));
    await userEvent.click(screen.getByRole("button", { name: "Scan to PDF" }));
    await screen.findByRole("link", { name: "Download" });
    const scan = calls.find((c) => c.url === "/api/scan")!;
    expect(scan.form.get("ocr")).toBe("true");
    expect(scan.form.get("languages")).toBe("eng,ind");
  });

  it("shows a server error from the scan request", async () => {
    handler = ({ url }) =>
      url === "/api/scan/preview"
        ? Promise.resolve({ image: "data:image/jpeg;base64,AAAA", cropped: true })
        : Promise.reject(new ApiError("'a.jpg' is corrupted or not a valid image.", 422));
    render(<ScanPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), photo("a.jpg"));
    await userEvent.click(screen.getByRole("button", { name: "Scan to PDF" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("corrupted"));
  });
});
