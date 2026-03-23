import { http, HttpResponse } from "msw";
import type { AnalysisResult, LogsResponse, Machine } from "@/types";

export const mockMachines: Machine[] = [
  {
    machine_id: "MCH-01",
    total_logs: 150,
    error_count: 3,
    warning_count: 8,
    operational_count: 139,
    last_seen: "2026-03-22T10:00:00Z",
  },
  {
    machine_id: "MCH-02",
    total_logs: 120,
    error_count: 2,
    warning_count: 5,
    operational_count: 113,
    last_seen: "2026-03-22T10:00:00Z",
  },
];

export const mockAnalysis: AnalysisResult = {
  id: 1,
  status: "complete",
  retry_count: 0,
  model_used: "gpt-4o-mini",
  provider: "openai",
  error_message: null,
  top_at_risk_machines: [
    {
      machine_id: "MCH-01",
      risk_level: "high",
      risk_score: 0.91,
      reason: "Multiple errors detected",
      affected_sensors: ["temperature"],
      recommended_action: "Inspect immediately",
    },
  ],
  fleet_summary: "1 machine at high risk",
  created_at: "2026-03-22T10:00:00Z",
  completed_at: "2026-03-22T10:00:05Z",
};

export const mockLogsResponse: LogsResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
  pages: 0,
};

export const handlers = [
  http.get("/api/machines", () => HttpResponse.json(mockMachines)),
  http.get("/api/analysis/latest", () => HttpResponse.json(mockAnalysis)),
  http.post("/api/analysis/run", () =>
    HttpResponse.json({ job_id: 1, status: "pending" })
  ),
  http.get("/api/logs", () => HttpResponse.json(mockLogsResponse)),
];
