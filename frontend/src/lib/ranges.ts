const PART = /^(\d+)(?:(-)(\d*))?$/;

/**
 * Check a page range such as "1-3,5,8-" against a document length.
 * Returns an error message, or null when the spec is valid.
 * Mirrors the server-side parser so users get feedback while typing.
 */
export function validateRanges(spec: string, totalPages: number): string | null {
  const cleaned = spec.replace(/\s+/g, "");
  if (cleaned === "") return "Enter the pages to extract, for example 1-3,5.";

  for (const part of cleaned.split(",")) {
    const match = PART.exec(part);
    if (!match) return `"${part}" is not a valid page range. Use formats like 3 or 2-5.`;

    const start = Number(match[1]);
    const end = match[2] === undefined ? start : match[3] === "" ? totalPages : Number(match[3]);

    if (start < 1 || end < 1) return "Page numbers start at 1.";
    if (start > end) return `"${part}" goes backwards. Write it as ${end}-${start}.`;
    if (end > totalPages) {
      return `"${part}" is outside the document, which has ${totalPages} page${totalPages === 1 ? "" : "s"}.`;
    }
  }
  return null;
}
