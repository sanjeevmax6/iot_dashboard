import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { SensorChart } from "@/components/SensorChart";
import { AnalysisFlashcard } from "@/components/chat/AnalysisFlashcard";
import { ChatBubble } from "@/components/chat/ChatBubble";
import { RiskSidebar } from "@/components/chat/RiskSidebar";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import { useLatestAnalysis, useRunAnalysis } from "@/hooks/useAnalysis";
import { useLogs } from "@/hooks/useLogs";

export function Trends() {
  const { data: analysis, isError } = useLatestAnalysis();
  const { run, isRunning } = useRunAnalysis();

  const hasResults = !!analysis?.top_at_risk_machines;

  const [selected, setSelected] = useState<string | null>(null);
  const topMachineId = selected ?? analysis?.top_at_risk_machines?.[0]?.machine_id ?? null;

  const { data: logsData } = useLogs({
    page: 1,
    page_size: 200,
    machine_id: topMachineId ?? undefined,
  });

  return (
    <div
      className={cn(
        "transition-all duration-500 ease-in-out px-6",
        hasResults
          ? "py-6 max-w-7xl mx-auto"
          : "flex flex-col items-center justify-center min-h-[calc(100vh-3.5rem)]"
      )}
    >
      {/* Main row: chat + sidebar */}
      <div
        className={cn(
          "flex gap-6 w-full transition-all duration-500",
          hasResults ? "items-start" : "justify-center"
        )}
      >
        {/* Chat column */}
        <div
          className={cn(
            "flex flex-col transition-all duration-500",
            hasResults ? "flex-1 min-w-0" : "w-full max-w-2xl"
          )}
        >
          {/* Message thread */}
          <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden flex flex-col">
            <div className="flex flex-col gap-5 p-5 min-h-[200px]">

              {/* Empty state */}
              {!hasResults && !isRunning && isError && (
                <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
                  <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mb-1">
                    <Sparkles className="w-5 h-5 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-700">Fleet analysis ready</p>
                  <p className="text-xs text-gray-400 max-w-xs">
                    Run an analysis to identify at-risk machines and get AI-powered maintenance recommendations.
                  </p>
                </div>
              )}

              {/* Prior result exists on load */}
              {hasResults && !isRunning && (
                <>
                  <ChatBubble role="user" delay={0}>
                    Analyze fleet health
                  </ChatBubble>

                  {analysis.fleet_summary && (
                    <ChatBubble role="ai" delay={100}>
                      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-700 leading-relaxed">
                        {analysis.fleet_summary}
                        {analysis.completed_at && (
                          <p className="text-xs text-gray-400 mt-2">
                            {formatDate(analysis.completed_at)}
                            {analysis.model_used && (
                              <span className="ml-2">· {analysis.model_used}</span>
                            )}
                          </p>
                        )}
                      </div>
                    </ChatBubble>
                  )}

                  {(analysis.top_at_risk_machines ?? []).map((m, i) => (
                    <ChatBubble key={m.machine_id} role="ai" delay={200 + i * 180}>
                      <AnalysisFlashcard machine={m} index={0} />
                    </ChatBubble>
                  ))}
                </>
              )}

              {/* Running state */}
              {isRunning && (
                <>
                  <ChatBubble role="user" delay={0}>
                    Analyze fleet health
                  </ChatBubble>
                  <TypingIndicator />
                </>
              )}
            </div>

            {/* Chat input bar */}
            <div className="border-t border-gray-100 px-4 py-3 flex items-center gap-3">
              <div className="flex-1 text-sm text-gray-400 select-none">
                {isRunning ? "Analyzing fleet data…" : "Ask the AI to analyze your fleet"}
              </div>
              <button
                onClick={() => run()}
                disabled={isRunning}
                className={cn(
                  "inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all",
                  isRunning
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-gray-900 text-white hover:bg-gray-700"
                )}
              >
                <span>{isRunning ? "Analyzing…" : "Run Analysis"}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar — slides in when results exist */}
        {hasResults && (
          <RiskSidebar
            machines={analysis.top_at_risk_machines ?? []}
            selected={selected}
            onSelect={setSelected}
          />
        )}
      </div>

      {/* Sensor chart — fades in below */}
      {hasResults && topMachineId && (
        <div className="mt-6 bg-white rounded-2xl border border-gray-200 p-5 animate-fade-in" style={{ opacity: 0 }}>
          <p className="text-sm font-semibold text-gray-700 mb-4">
            {topMachineId} — Sensor Trends
          </p>
          <SensorChart logs={logsData?.items ?? []} machineId={topMachineId} />
        </div>
      )}
    </div>
  );
}
