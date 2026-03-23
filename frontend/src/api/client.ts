import type {
  AnalysisResult,
  AnalysisRunResponse,
  IngestResponse,
  LogsResponse,
  Machine,
} from "@/types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  logs: {
    list: (params: {
      page?: number;
      page_size?: number;
      machine_id?: string;
      status?: string;
    }) => {
      const q = new URLSearchParams();
      if (params.page) q.set("page", String(params.page));
      if (params.page_size) q.set("page_size", String(params.page_size));
      if (params.machine_id) q.set("machine_id", params.machine_id);
      if (params.status) q.set("status", params.status);
      return get<LogsResponse>(`/logs?${q.toString()}`);
    },
    ingest: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${BASE}/logs/ingest`, { method: "POST", body: form }).then(
        (r) => {
          if (!r.ok) throw new Error(`Ingest failed: ${r.status}`);
          return r.json() as Promise<IngestResponse>;
        }
      );
    },
  },

  machines: {
    list: () => get<Machine[]>("/machines"),
    get: (id: string) => get<Machine>(`/machines/${id}`),
  },

  analysis: {
    run: () => post<AnalysisRunResponse>("/analysis/run"),
    status: (jobId: number) => get<AnalysisResult>(`/analysis/status/${jobId}`),
    latest: () => get<AnalysisResult>("/analysis/latest"),
  },

  data: {
    clear: () =>
      fetch(`${BASE}/data`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error(`Clear failed: ${r.status}`);
        return r.json() as Promise<{ cleared: boolean }>;
      }),
    ingestStream: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${BASE}/logs/ingest/stream`, { method: "POST", body: form });
    },
  },
};
