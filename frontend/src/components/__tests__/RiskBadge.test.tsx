import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskBadge } from "../RiskBadge";

describe("RiskBadge", () => {
  it("renders high risk text", () => {
    render(<RiskBadge level="high" />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("renders medium risk text", () => {
    render(<RiskBadge level="medium" />);
    expect(screen.getByText("medium")).toBeInTheDocument();
  });

  it("renders low risk text", () => {
    render(<RiskBadge level="low" />);
    expect(screen.getByText("low")).toBeInTheDocument();
  });

  it("applies red styling for high risk", () => {
    render(<RiskBadge level="high" />);
    expect(screen.getByText("high")).toHaveClass("text-red-700");
  });

  it("applies amber styling for medium risk", () => {
    render(<RiskBadge level="medium" />);
    expect(screen.getByText("medium")).toHaveClass("text-amber-700");
  });

  it("applies green styling for low risk", () => {
    render(<RiskBadge level="low" />);
    expect(screen.getByText("low")).toHaveClass("text-green-700");
  });
});
