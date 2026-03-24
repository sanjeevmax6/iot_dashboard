import { CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

// Exporing so I can do type check/filter at dashboard
export type IngestState =
  | { phase: "idle" }
  | { phase: "streaming"; processed: number; total: number; machine_id: string; timestamp: string; inserted: number; skipped: number }
  | { phase: "complete"; inserted: number; skipped: number; total_rows: number }
  | { phase: "error"; message: string };

interface Props {
  state: IngestState;
  onClose: () => void;
}

export function IngestModal({ state, onClose }: Props) {
  if (state.phase === "idle") return null;

  const progress =
    state.phase === "streaming"
      ? Math.round((state.processed / state.total) * 100)
      : state.phase === "complete"
      ? 100
      : 0;

  const isDone = state.phase === "complete" || state.phase === "error";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 flex flex-col gap-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            {state.phase === "complete"
              ? "Ingest Complete"
              : state.phase === "error"
              ? "Ingest Failed"
              : "Ingesting CSV…"}
          </h2>
          {isDone && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            >
              ✕
            </button>
          )}
        </div>

        {/* Progress bar */}
        {state.phase !== "error" && (
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-xs text-gray-500">
              <span>
                {state.phase === "streaming"
                  ? `${state.processed.toLocaleString()} / ${state.total.toLocaleString()} rows`
                  : `${state.phase === "complete" ? state.total_rows.toLocaleString() : "0"} rows`}
              </span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  state.phase === "complete" ? "bg-green-500" : "bg-blue-500"
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Current record */}
        {state.phase === "streaming" && (
          <div className="bg-gray-50 rounded-lg px-3 py-2 text-xs font-mono text-gray-600 truncate">
            <span className="text-gray-400 mr-2">Processing</span>
            <span className="font-semibold text-gray-800">{state.machine_id}</span>
            <span className="text-gray-400 mx-1">@</span>
            {state.timestamp.replace("T", " ").slice(0, 19)}
          </div>
        )}

        {/* Summary on complete */}
        {state.phase === "complete" && (
          <div className="flex gap-3">
            <div className="flex-1 bg-green-50 border border-green-200 rounded-lg p-3 text-center">
              <CheckCircle className="w-5 h-5 text-green-600 mx-auto mb-1" />
              <p className="text-xl font-bold text-green-700">{state.inserted.toLocaleString()}</p>
              <p className="text-xs text-green-600">Inserted</p>
            </div>
            {state.skipped > 0 && (
              <div className="flex-1 bg-amber-50 border border-amber-200 rounded-lg p-3 text-center">
                <p className="text-xl font-bold text-amber-700">{state.skipped.toLocaleString()}</p>
                <p className="text-xs text-amber-600">Skipped (duplicates)</p>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {state.phase === "error" && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
            <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
            <p className="text-sm text-red-700">{state.message}</p>
          </div>
        )}

        {/* Inline stats during streaming */}
        {state.phase === "streaming" && (
          <div className="flex gap-4 text-xs text-gray-500">
            <span>
              <span className="font-semibold text-gray-700">{state.inserted.toLocaleString()}</span> inserted
            </span>
            <span>
              <span className="font-semibold text-gray-700">{state.skipped.toLocaleString()}</span> skipped
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
