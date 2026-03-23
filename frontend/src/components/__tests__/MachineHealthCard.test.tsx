import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MachineHealthCard } from "../MachineHealthCard";
import type { MachineRisk } from "@/types";

const highRisk: MachineRisk = {
  machine_id: "MCH-08",
  risk_level: "high",
  risk_score: 0.91,
  reason: "4 errors in 4 days, temp peaks at 102°F",
  affected_sensors: ["temperature", "vibration"],
  recommended_action: "Immediate inspection of thermal system",
};

describe("MachineHealthCard", () => {
  it("renders the machine id", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(screen.getByText("MCH-08")).toBeInTheDocument();
  });

  it("renders the risk score formatted to 2 decimal places", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(screen.getByText("0.91")).toBeInTheDocument();
  });

  it("renders the reason text", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(
      screen.getByText("4 errors in 4 days, temp peaks at 102°F")
    ).toBeInTheDocument();
  });

  it("renders all affected sensor chips", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(screen.getByText("temperature")).toBeInTheDocument();
    expect(screen.getByText("vibration")).toBeInTheDocument();
  });

  it("renders the recommended action", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(
      screen.getByText("Immediate inspection of thermal system")
    ).toBeInTheDocument();
  });

  it("renders a RiskBadge with the correct level", () => {
    render(<MachineHealthCard machine={highRisk} />);
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("applies red border styling for high risk", () => {
    const { container } = render(<MachineHealthCard machine={highRisk} />);
    expect(container.firstChild).toHaveClass("border-red-200");
  });

  it("applies amber border styling for medium risk", () => {
    const mediumRisk: MachineRisk = {
      ...highRisk,
      risk_level: "medium",
      risk_score: 0.55,
    };
    const { container } = render(<MachineHealthCard machine={mediumRisk} />);
    expect(container.firstChild).toHaveClass("border-amber-200");
  });

  it("applies green border styling for low risk", () => {
    const lowRisk: MachineRisk = {
      ...highRisk,
      risk_level: "low",
      risk_score: 0.2,
    };
    const { container } = render(<MachineHealthCard machine={lowRisk} />);
    expect(container.firstChild).toHaveClass("border-green-200");
  });

  it("hides sensor chips when none are affected", () => {
    const noSensors: MachineRisk = { ...highRisk, affected_sensors: [] };
    render(<MachineHealthCard machine={noSensors} />);
    expect(screen.queryByText("temperature")).not.toBeInTheDocument();
    expect(screen.queryByText("vibration")).not.toBeInTheDocument();
  });
});
