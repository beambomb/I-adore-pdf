import { describe, expect, it } from "vitest";
import { validateRanges } from "./ranges";

describe("validateRanges", () => {
  it.each(["1-3,5", "8-", " 5 , 1-2 ", "1", "10"])("accepts %j", (spec) => {
    expect(validateRanges(spec, 10)).toBeNull();
  });

  it.each(["", "   ", "abc", "0", "0-2", "5-3", "11", "1-11", "1,,2", "1--2", "-3", "1-2-3"])(
    "rejects %j",
    (spec) => {
      expect(validateRanges(spec, 10)).not.toBeNull();
    },
  );

  it("mentions the document size when out of range", () => {
    expect(validateRanges("12", 10)).toContain("10 pages");
    expect(validateRanges("2", 1)).toContain("1 page.");
  });
});
