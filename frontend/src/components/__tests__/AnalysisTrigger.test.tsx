import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AnalysisTrigger } from "../AnalysisTrigger";
import { useRunAnalysis } from "@/hooks/useAnalysis";

vi.mock("@/hooks/useAnalysis");

const mockUseRunAnalysis = vi.mocked(useRunAnalysis);

describe("AnalysisTrigger", () => {
  it("renders Run Analysis button when idle", () => {
    mockUseRunAnalysis.mockReturnValue({
      run: vi.fn(),
      isRunning: false,
      jobStatus: undefined,
    });
    render(<AnalysisTrigger />);
    expect(
      screen.getByRole("button", { name: /run analysis/i })
    ).toBeInTheDocument();
  });

  it("button is enabled when not running", () => {
    mockUseRunAnalysis.mockReturnValue({
      run: vi.fn(),
      isRunning: false,
      jobStatus: undefined,
    });
    render(<AnalysisTrigger />);
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("shows Analyzing text while running", () => {
    mockUseRunAnalysis.mockReturnValue({
      run: vi.fn(),
      isRunning: true,
      jobStatus: "running",
    });
    render(<AnalysisTrigger />);
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
  });

  it("disables the button while running", () => {
    mockUseRunAnalysis.mockReturnValue({
      run: vi.fn(),
      isRunning: true,
      jobStatus: "running",
    });
    render(<AnalysisTrigger />);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls run() when button is clicked", async () => {
    const mockRun = vi.fn();
    mockUseRunAnalysis.mockReturnValue({
      run: mockRun,
      isRunning: false,
      jobStatus: undefined,
    });
    render(<AnalysisTrigger />);
    await userEvent.click(screen.getByRole("button"));
    expect(mockRun).toHaveBeenCalledOnce();
  });
});
