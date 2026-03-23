import { Loader2, Zap } from "lucide-react";
import { useRunAnalysis } from "@/hooks/useAnalysis";

export function AnalysisTrigger() {
  const { run, isRunning } = useRunAnalysis();

  return (
    <button
      onClick={() => run()}
      disabled={isRunning}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
    >
      {isRunning ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          Analyzing…
        </>
      ) : (
        <>
          <Zap className="w-4 h-4" />
          Run Analysis
        </>
      )}
    </button>
  );
}
