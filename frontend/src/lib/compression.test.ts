import { describe, expect, it } from "vitest";
import { describeSavings, type CompressResult } from "./compression";

const base: CompressResult = {
  job_id: "a".repeat(32),
  filename: "x-compressed.pdf",
  size: 0,
  media_type: "application/pdf",
  download_url: "/api/download/x",
  original_size: 5 * 1024 * 1024,
  compressed_size: 1024 * 1024,
  saved_percent: 80,
  already_optimal: false,
};

describe("describeSavings", () => {
  it("shows before, after and percentage", () => {
    expect(describeSavings(base)).toBe("5.0 MB → 1.0 MB (-80%)");
  });

  it("keeps one decimal for fractional percentages", () => {
    expect(describeSavings({ ...base, saved_percent: 12.5 })).toContain("(-12.5%)");
  });

  it("explains when the original was kept", () => {
    const text = describeSavings({ ...base, compressed_size: base.original_size, already_optimal: true });
    expect(text).toContain("could not be made smaller");
    expect(text).not.toContain("→");
  });
});
