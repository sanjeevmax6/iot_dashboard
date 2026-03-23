import { useState } from "react";
import { formatDate } from "@/lib/utils";
import { AnalysisTrigger } from "@/components/AnalysisTrigger";
import { MachineHealthCard } from "@/components/MachineHealthCard";
import { SensorChart } from "@/components/SensorChart";
import { useLatestAnalysis } from "@/hooks/useAnalysis";
import { useLogs } from "@/hooks/useLogs";

export function Trends() {
  const { data: analysis, isLoading, isError } = useLatestAnalysis();
  const [selectedMachine, setSelectedMachine] = useState<string | null>(null);

  const topMachineId =
    selectedMachine ?? analysis?.top_at_risk_machines?.[0]?.machine_id ?? null;

  const { data: logsData } = useLogs({
    page: 1,
    page_size: 200,
    machine_id: topMachineId ?? undefined,
  });

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Health Trends</h1>
          {analysis?.completed_at && (
            <p className="text-sm text-gray-500 mt-0.5">
              Last analysis: {formatDate(analysis.completed_at)}
              {analysis.model_used && (
                <span className="ml-2 text-xs text-gray-400">
                  via {analysis.model_used}
                </span>
              )}
            </p>
          )}
        </div>
        <AnalysisTrigger />
      </div>

      {isLoading && (
        <div className="bg-white rounded-lg border border-gray-200 p-10 text-center text-sm text-gray-400">
          Loading analysis…
        </div>
      )}

      {isError && (
        <div className="bg-white rounded-lg border border-gray-200 p-10 text-center">
          <p className="text-sm text-gray-500">No analysis results yet.</p>
          <p className="text-xs text-gray-400 mt-1">Run an analysis to see AI health insights.</p>
        </div>
      )}

      {analysis?.status === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Analysis failed: {analysis.error_message}
        </div>
      )}

      {analysis?.top_at_risk_machines && (
        <>
          {analysis.fleet_summary && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
              {analysis.fleet_summary}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {analysis.top_at_risk_machines.map((m) => (
              <button
                key={m.machine_id}
                onClick={() => setSelectedMachine(m.machine_id)}
                className="text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg"
              >
                <MachineHealthCard machine={m} />
              </button>
            ))}
          </div>

          {topMachineId && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <p className="text-sm font-semibold text-gray-700 mb-4">
                {topMachineId} — Sensor Trends
              </p>
              <SensorChart
                logs={logsData?.items ?? []}
                machineId={topMachineId}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
