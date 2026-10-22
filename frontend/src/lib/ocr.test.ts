import { describe, expect, it } from "vitest";
import { toLanguagesParam, toggleLanguage } from "./ocr";

describe("toLanguagesParam", () => {
  it("joins selected languages in UI order", () => {
    expect(toLanguagesParam(["ind", "eng"])).toBe("eng,ind");
    expect(toLanguagesParam(["ind"])).toBe("ind");
  });
});

describe("toggleLanguage", () => {
  it("adds and removes languages", () => {
    expect(toggleLanguage(["eng"], "ind")).toEqual(["eng", "ind"]);
    expect(toggleLanguage(["eng", "ind"], "eng")).toEqual(["ind"]);
  });

  it("never leaves the selection empty", () => {
    expect(toggleLanguage(["eng"], "eng")).toEqual(["eng"]);
  });
});
