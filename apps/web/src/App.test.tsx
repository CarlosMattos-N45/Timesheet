import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renderiza o título do produto como heading h1", () => {
    render(<App />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /TimeSheet Terceiros/i,
    });
    expect(heading).toBeInTheDocument();
  });

  it("usa Typography do MUI no heading", () => {
    render(<App />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /TimeSheet Terceiros/i,
    });
    // MUI Typography variant=h4 aplica classe que começa com "MuiTypography"
    expect(heading.className).toMatch(/MuiTypography/);
  });
});
