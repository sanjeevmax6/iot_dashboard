import { useRef, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { FleetStatsBar } from "@/components/FleetStatsBar";
import { IngestModal, type IngestState } from "@/components/IngestModal";
import { LogsTable } from "@/components/LogsTable";
import { useLogs } from "@/hooks/useLogs";
import { useMachines } from "@/hooks/useMachines";

const PAGE_SIZE = 20;

export function Dashboard() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ machine_id: "", status: "" });
  const [ingestState, setIngestState] = useState<IngestState>({ phase: "idle" });
  const [clearing, setClearing] = useState(false);

  const { data: logsData, isLoading: logsLoading } = useLogs({ page, page_size: PAGE_SIZE, ...filters });
  const { data: machines = [] } = useMachines();

  function handleFilterChange(key: "machine_id" | "status", value: string) {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  }

  async function handleIngest(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (fileRef.current) fileRef.current.value = "";

    setIngestState({ phase: "streaming", processed: 0, total: 0, machine_id: "", timestamp: "", inserted: 0, skipped: 0 });

    try {
      const response = await api.data.ingestStream(file);
      if (!response.ok) {
        setIngestState({ phase: "error", message: `Upload failed (${response.status})` });
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const event = JSON.parse(line.slice(6)) as Record<string, unknown>;

          if (event.type === "progress") {
            setIngestState({
              phase: "streaming",
              processed: event.processed as number,
              total: event.total as number,
              machine_id: event.machine_id as string,
              timestamp: event.timestamp as string,
              inserted: event.inserted as number,
              skipped: event.skipped as number,
            });
          } else if (event.type === "complete") {
            setIngestState({
              phase: "complete",
              inserted: event.inserted as number,
              skipped: event.skipped as number,
              total_rows: event.total_rows as number,
            });
            void queryClient.invalidateQueries({ queryKey: ["logs"] });
            void queryClient.invalidateQueries({ queryKey: ["machines"] });
          } else if (event.type === "error") {
            setIngestState({ phase: "error", message: event.message as string });
          }
        }
      }
    } catch {
      setIngestState({ phase: "error", message: "Network error during ingest." });
    }
  }

  async function handleClear() {
    if (!confirm("This will delete all logs, machines, and analysis results. Continue?")) return;
    setClearing(true);
    try {
      await api.data.clear();
      toast.success("All data cleared.");
      void queryClient.invalidateQueries();
    } catch {
      toast.error("Failed to clear data.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <>
      <IngestModal
        state={ingestState}
        onClose={() => setIngestState({ phase: "idle" })}
      />

      <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClear}
              disabled={clearing}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium text-red-600 hover:bg-red-50 hover:border-red-200 disabled:opacity-50 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              {clearing ? "Clearing…" : "Clear Data"}
            </button>
            <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer transition-colors">
              <Upload className="w-4 h-4" />
              Ingest CSV
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleIngest} />
            </label>
          </div>
        </div>

        <FleetStatsBar machines={machines} totalLogs={logsData?.total ?? 0} />

        {logsLoading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-10 text-center text-sm text-gray-400">
            Loading logs…
          </div>
        ) : (
          <LogsTable
            logs={logsData?.items ?? []}
            total={logsData?.total ?? 0}
            page={page}
            pages={logsData?.pages ?? 1}
            machines={machines}
            filters={filters}
            onPageChange={setPage}
            onFilterChange={handleFilterChange}
          />
        )}
      </div>
    </>
  );
}
