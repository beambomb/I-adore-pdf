import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import MergePage from "./MergePage";

// A plain function (not vi.fn) is used for the mock so rejected promises are not
// re-tracked by the spy and reported as unhandled rejections.
let handler: (...args: unknown[]) => Promise<unknown> = () => Promise.resolve({});
let calls: unknown[][] = [];

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    postForm: (...args: unknown[]) => {
      calls.push(args);
      return handler(...args);
    },
  };
});

const pdf = (name: string) => new File(["%PDF-1.7"], name, { type: "application/pdf" });

async function addFiles(...names: string[]) {
  await userEvent.upload(screen.getByLabelText("Choose files"), names.map(pdf));
}

function listedNames() {
  return within(screen.getByRole("list", { name: "Selected files" }))
    .getAllByRole("listitem")
    .map((li) => li.querySelector(".file-list__name")!.textContent);
}

beforeEach(() => {
  calls = [];
  handler = () => Promise.resolve({});
});

describe("MergePage", () => {
  it("keeps the merge button disabled until two files are selected", async () => {
    render(<MergePage />);
    const button = screen.getByRole("button", { name: "Merge PDF" });
    expect(button).toBeDisabled();
    await addFiles("a.pdf");
    expect(button).toBeDisabled();
    await addFiles("b.pdf");
    expect(button).toBeEnabled();
  });

  it("reorders and removes files", async () => {
    render(<MergePage />);
    await addFiles("a.pdf", "b.pdf", "c.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Move c.pdf up" }));
    expect(listedNames()).toEqual(["a.pdf", "c.pdf", "b.pdf"]);
    await userEvent.click(screen.getByRole("button", { name: "Remove a.pdf" }));
    expect(listedNames()).toEqual(["c.pdf", "b.pdf"]);
  });

  it("sends files in the displayed order and shows the download link", async () => {
    handler = () =>
      Promise.resolve({
        job_id: "1".repeat(32),
        filename: "merged.pdf",
        size: 2048,
        media_type: "application/pdf",
        download_url: "/api/download/" + "1".repeat(32),
      });
    render(<MergePage />);
    await addFiles("a.pdf", "b.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Move b.pdf up" }));
    await userEvent.click(screen.getByRole("button", { name: "Merge PDF" }));

    const link = await screen.findByRole("link", { name: "Download" });
    expect(link).toHaveAttribute("href", "/api/download/" + "1".repeat(32));

    const [url, form] = calls[0] as [string, FormData];
    expect(url).toBe("/api/merge");
    expect(form.getAll("files").map((f) => (f as File).name)).toEqual(["b.pdf", "a.pdf"]);
  });

  it("shows the server error message", async () => {
    handler = () => Promise.reject(new ApiError("'b.pdf' is corrupted or not a valid PDF.", 422));
    render(<MergePage />);
    await addFiles("a.pdf", "b.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Merge PDF" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("corrupted"));
    expect(screen.getByRole("button", { name: "Merge PDF" })).toBeEnabled();
  });
});
