import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import ImageToPdfPage from "./ImageToPdfPage";

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

const result = {
  job_id: "3".repeat(32),
  filename: "images.pdf",
  size: 4096,
  media_type: "application/pdf",
  download_url: "/api/download/" + "3".repeat(32),
};

const image = (name: string, type = "image/png") => new File(["img"], name, { type });

beforeEach(() => {
  calls = [];
  handler = () => Promise.resolve(result);
  // jsdom does not implement object URLs.
  URL.createObjectURL = vi.fn(() => "blob:mock");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => vi.restoreAllMocks());

describe("ImageToPdfPage", () => {
  it("disables convert until an image is added and shows thumbnails", async () => {
    const { container } = render(<ImageToPdfPage />);
    expect(screen.getByRole("button", { name: "Convert to PDF" })).toBeDisabled();
    await userEvent.upload(screen.getByLabelText("Choose files"), image("a.png"));
    expect(screen.getByRole("button", { name: "Convert to PDF" })).toBeEnabled();
    await waitFor(() => expect(container.querySelector(".file-list__thumb")).not.toBeNull());
  });

  it("rejects non-image files", async () => {
    render(<ImageToPdfPage />);
    const pdf = new File(["%PDF"], "doc.pdf", { type: "application/pdf" });
    // fireEvent-style upload bypasses the input's accept filter in userEvent only when applyAccept is off.
    await userEvent.upload(screen.getByLabelText("Choose files"), pdf, { applyAccept: false } as never);
    expect(screen.getByRole("alert")).toHaveTextContent("unsupported file type");
    expect(screen.getByRole("button", { name: "Convert to PDF" })).toBeDisabled();
  });

  it("shows the orientation option only for A4", async () => {
    render(<ImageToPdfPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), image("a.png"));
    expect(screen.queryByLabelText("Orientation")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Page size"), "a4");
    expect(screen.getByLabelText("Orientation")).toBeInTheDocument();
  });

  it("sends images in order with the chosen options", async () => {
    render(<ImageToPdfPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), [image("a.png"), image("b.jpg", "image/jpeg")]);
    await userEvent.click(screen.getByRole("button", { name: "Move b.jpg up" }));
    await userEvent.selectOptions(screen.getByLabelText("Page size"), "a4");
    await userEvent.selectOptions(screen.getByLabelText("Orientation"), "landscape");
    await userEvent.click(screen.getByRole("button", { name: "Convert to PDF" }));

    expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      result.download_url,
    );
    const [url, form] = calls[0];
    expect(url).toBe("/api/image-to-pdf");
    expect(form.getAll("files").map((f) => (f as File).name)).toEqual(["b.jpg", "a.png"]);
    expect(form.get("page_size")).toBe("a4");
    expect(form.get("orientation")).toBe("landscape");
  });

  it("shows the server error", async () => {
    handler = () => Promise.reject(new ApiError("'a.png' is corrupted or not a valid image.", 422));
    render(<ImageToPdfPage />);
    await userEvent.upload(screen.getByLabelText("Choose files"), image("a.png"));
    await userEvent.click(screen.getByRole("button", { name: "Convert to PDF" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("corrupted"));
  });
});
