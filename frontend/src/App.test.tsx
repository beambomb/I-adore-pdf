import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";
import { tools } from "./tools";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing", () => {
  it("renders the home page inside the layout", () => {
    renderAt("/");
    expect(screen.getByRole("link", { name: /I-adore-pdf/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/tool you need/i);
  });

  it("lists every tool in the header navigation and highlights the current one", () => {
    renderAt("/merge");
    const nav = screen.getByRole("navigation", { name: "Tools" });
    const links = nav.querySelectorAll("a");
    expect(links).toHaveLength(tools.length);
    expect(tools).toHaveLength(6); // merge, split, image to pdf, compress, scan, ocr
    expect(screen.getByRole("link", { name: "Merge PDF", current: "page" })).toBeInTheDocument();
  });

  it("renders a not-found page for unknown routes", () => {
    renderAt("/does-not-exist");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Page not found");
  });
});
