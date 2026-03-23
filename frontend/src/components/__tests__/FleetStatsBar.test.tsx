import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FleetStatsBar } from "../FleetStatsBar";
import type { Machine } from "@/types";

const twoMachines: Machine[] = [
  {
    machine_id: "MCH-01",
    total_logs: 150,
    error_count: 3,
    warning_count: 8,
    operational_count: 139,
    last_seen: null,
  },
  {
    machine_id: "MCH-02",
    total_logs: 100,
    error_count: 2,
    warning_count: 5,
    operational_count: 93,
    last_seen: null,
  },
];

describe("FleetStatsBar", () => {
  it("shows all four stat labels", () => {
    render(<FleetStatsBar machines={twoMachines} totalLogs={250} />);
    expect(screen.getByText("Machines")).toBeInTheDocument();
    expect(screen.getByText("Total Logs")).toBeInTheDocument();
    expect(screen.getByText("Errors")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
  });

  it("shows correct machine count", () => {
    render(<FleetStatsBar machines={twoMachines} totalLogs={250} />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows formatted total logs", () => {
    render(<FleetStatsBar machines={twoMachines} totalLogs={1000} />);
    expect(screen.getByText("1,000")).toBeInTheDocument();
  });

  it("sums errors across all machines", () => {
    render(<FleetStatsBar machines={twoMachines} totalLogs={250} />);
    expect(screen.getByText("5")).toBeInTheDocument(); // 3 + 2
  });

  it("sums warnings across all machines", () => {
    render(<FleetStatsBar machines={twoMachines} totalLogs={250} />);
    expect(screen.getByText("13")).toBeInTheDocument(); // 8 + 5
  });

  it("renders zero state with empty machines list", () => {
    render(<FleetStatsBar machines={[]} totalLogs={0} />);
    expect(screen.getByText("Machines")).toBeInTheDocument();
    // machine count, errors, warnings all zero — check at least one
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBeGreaterThanOrEqual(3);
  });
});
