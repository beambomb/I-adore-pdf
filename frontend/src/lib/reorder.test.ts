import { describe, expect, it } from "vitest";
import { moveItem, removeAt } from "./reorder";

describe("moveItem", () => {
  it("moves an item forward and backward", () => {
    expect(moveItem(["a", "b", "c"], 0, 2)).toEqual(["b", "c", "a"]);
    expect(moveItem(["a", "b", "c"], 2, 0)).toEqual(["c", "a", "b"]);
  });

  it("ignores out-of-range or no-op moves and never mutates the input", () => {
    const input = ["a", "b"];
    expect(moveItem(input, 0, 5)).toEqual(["a", "b"]);
    expect(moveItem(input, -1, 0)).toEqual(["a", "b"]);
    expect(moveItem(input, 1, 1)).toEqual(["a", "b"]);
    expect(input).toEqual(["a", "b"]);
  });
});

describe("removeAt", () => {
  it("removes by index without mutating", () => {
    const input = ["a", "b", "c"];
    expect(removeAt(input, 1)).toEqual(["a", "c"]);
    expect(input).toHaveLength(3);
  });
});
