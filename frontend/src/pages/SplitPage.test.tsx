import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import SplitPage from "./SplitPage";

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
  job_id: "2".repeat(32),
  filename: "doc-split.pdf",
  size: 1024,
  media_type: "application/pdf",
  download_url: "/api/download/" + "2".repeat(32),
};

beforeEach(() => {
  calls = [];
  handler = (url) =>
    Promise.resolve(url === "/api/split/info" ? { filename: "doc.pdf", pages: 10 } : result);
});

async function chooseFile() {
  const file = new File(["%PDF-1.7"], "doc.pdf", { type: "application/pdf" });
  await userEvent.upload(screen.getByLabelText("Choose files"), file);
  // The options only appear once the page count has been loaded.
  await screen.findByLabelText("Pages to extract");
}

describe("SplitPage", () => {
  it("shows the page count after choosing a file", async () => {
    render(<SplitPage />);
    expect(screen.getByRole("button", { name: "Split PDF" })).toBeDisabled();
    await chooseFile();
    expect(calls[0][0]).toBe("/api/split/info");
    expect(screen.getByText(/\(8 B, 10 pages\)/)).toBeInTheDocument();
  });

  it("validates ranges live and enables the button only for valid input", async () => {
    render(<SplitPage />);
    await chooseFile();
    const input = screen.getByLabelText("Pages to extract");
    const button = screen.getByRole("button", { name: "Split PDF" });

    await userEvent.type(input, "1-99");
    expect(screen.getByText(/outside the document/)).toBeInTheDocument();
    expect(button).toBeDisabled();

    await userEvent.clear(input);
    await userEvent.type(input, "1-3,5");
    expect(button).toBeEnabled();
  });

  it("sends the ranges and shows the download link", async () => {
    render(<SplitPage />);
    await chooseFile();
    await userEvent.type(screen.getByLabelText("Pages to extract"), "1-3,5");
    await userEvent.click(screen.getByRole("button", { name: "Split PDF" }));

    expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      result.download_url,
    );
    const [url, form] = calls[1];
    expect(url).toBe("/api/split");
    expect(form.get("mode")).toBe("ranges");
    expect(form.get("ranges")).toBe("1-3,5");
  });

  it("supports splitting every page without a range", async () => {
    render(<SplitPage />);
    await chooseFile();
    await userEvent.click(screen.getByLabelText(/every page/));
    expect(screen.queryByLabelText("Pages to extract")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Split PDF" }));
    await screen.findByRole("link", { name: "Download" });
    const form = calls[1][1];
    expect(form.get("mode")).toBe("all");
    expect(form.has("ranges")).toBe(false);
  });

  it("shows an error and clears the file when the PDF cannot be read", async () => {
    handler = () => Promise.reject(new ApiError("'doc.pdf' is corrupted or not a valid PDF.", 422));
    render(<SplitPage />);
    const file = new File(["%PDF-1.7"], "doc.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Choose files"), file);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("corrupted"));
    expect(screen.getByLabelText("Choose files")).toBeInTheDocument();
  });
});
