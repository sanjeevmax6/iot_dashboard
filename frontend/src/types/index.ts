export interface LogEntry {
  id: number;
  machine_id: string;
  timestamp: string;
  temperature: number;
  vibration: number;
  status: "OPERATIONAL" | "WARNING" | "ERROR";
}

export interface LogsResponse {
  items: LogEntry[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Machine {
  machine_id: string;
  total_logs: number;
  error_count: number;
  warning_count: number;
  operational_count: number;
  last_seen: string | null;
}

export interface MachineRisk {
  machine_id: string;
  risk_level: "high" | "medium" | "low";
  risk_score: number;
  reason: string;
  affected_sensors: string[];
  recommended_action: string;
}

export interface AnalysisResult {
  id: number;
  status: "pending" | "running" | "complete" | "error";
  retry_count: number;
  model_used: string | null;
  provider: string | null;
  error_message: string | null;
  top_at_risk_machines: MachineRisk[] | null;
  fleet_summary: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisRunResponse {
  job_id: number;
  status: string;
}

export interface IngestResponse {
  inserted: number;
  skipped: number;
  machines_found: number;
  total_rows: number;
}
