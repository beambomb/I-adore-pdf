import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import FileDropzone, { matchesAccept } from "./FileDropzone";

const pdf = (name = "a.pdf", size = 10) =>
  new File([new Uint8Array(size)], name, { type: "application/pdf" });

describe("matchesAccept", () => {
  it("matches by MIME type or extension", () => {
    expect(matchesAccept(pdf(), ["application/pdf"])).toBe(true);
    expect(matchesAccept(new File(["x"], "B.PDF"), [".pdf"])).toBe(true);
    expect(matchesAccept(new File(["x"], "b.txt", { type: "text/plain" }), ["application/pdf", ".pdf"])).toBe(false);
  });
});

describe("FileDropzone", () => {
  it("passes accepted files to onFiles", async () => {
    const onFiles = vi.fn();
    render(<FileDropzone accept={["application/pdf"]} multiple onFiles={onFiles} />);
    await userEvent.upload(screen.getByLabelText("Choose files"), [pdf("a.pdf"), pdf("b.pdf")]);
    expect(onFiles).toHaveBeenCalledTimes(1);
    expect(onFiles.mock.calls[0][0].map((f: File) => f.name)).toEqual(["a.pdf", "b.pdf"]);
  });

  it("rejects files of the wrong type and shows an error", () => {
    const onFiles = vi.fn();
    render(<FileDropzone accept={["application/pdf"]} onFiles={onFiles} />);
    const bad = new File(["x"], "notes.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Choose files"), { target: { files: [bad] } });
    expect(onFiles).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("notes.txt: unsupported file type.");
  });

  it("rejects files over the size limit", () => {
    const onFiles = vi.fn();
    render(<FileDropzone accept={["application/pdf"]} maxFileBytes={5} onFiles={onFiles} />);
    fireEvent.change(screen.getByLabelText("Choose files"), { target: { files: [pdf("big.pdf", 20)] } });
    expect(onFiles).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("big.pdf");
  });

  it("accepts dropped files", () => {
    const onFiles = vi.fn();
    const { container } = render(<FileDropzone accept={["application/pdf"]} onFiles={onFiles} />);
    const zone = container.querySelector(".dropzone")!;
    fireEvent.drop(zone, { dataTransfer: { files: [pdf("dropped.pdf")] } });
    expect(onFiles).toHaveBeenCalledTimes(1);
  });

  it("keeps only the first file when multiple is off", () => {
    const onFiles = vi.fn();
    render(<FileDropzone accept={["application/pdf"]} onFiles={onFiles} />);
    fireEvent.change(screen.getByLabelText("Choose files"), {
      target: { files: [pdf("one.pdf"), pdf("two.pdf")] },
    });
    expect(onFiles.mock.calls[0][0]).toHaveLength(1);
    expect(screen.getByRole("alert")).toHaveTextContent("Only one file");
  });
});
