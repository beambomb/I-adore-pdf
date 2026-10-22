export interface ToolInfo {
  path: string;
  title: string;
  description: string;
}

/** Every implemented tool. Each task appends its own entry here. */
export const tools: ToolInfo[] = [
  {
    path: "/merge",
    title: "Merge PDF",
    description: "Combine several PDF files into a single document.",
  },
  {
    path: "/split",
    title: "Split PDF",
    description: "Extract page ranges or save every page as its own PDF.",
  },
  {
    path: "/image-to-pdf",
    title: "Image to PDF",
    description: "Convert JPG, PNG or WEBP images into a PDF document.",
  },
];
