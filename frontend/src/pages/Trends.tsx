import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Bot, ChevronLeft, ChevronRight } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { SensorChart } from "@/components/SensorChart";
import { ChatInput } from "@/components/chat/ChatInput";
import { RiskSidebar } from "@/components/chat/RiskSidebar";
import { ThoughtsPanel } from "@/components/chat/ThoughtsPanel";
import { useChat, type ChatMessage } from "@/hooks/useChat";
import { useLatestAnalysis } from "@/hooks/useAnalysis";
import { useLogs } from "@/hooks/useLogs";
import type { MachineRisk } from "@/types";

// Stable session id for this page mount
const SESSION_ID = Math.random().toString(36).slice(2);

// Attempt to parse top_at_risk_machines from an AI message that was a narration
function extractMachinesFromAnalysis(latestMachines: MachineRisk[] | null | undefined) {
  return latestMachines ?? [];
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-600 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-sm">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <div className="w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center shrink-0 mt-0.5">
        <Bot className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <ThoughtsPanel thoughts={msg.thoughts} isStreaming={msg.isStreaming} />
        {msg.content && (
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            {msg.content}
          </div>
        )}
        {msg.isStreaming && !msg.content && (
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        )}
      </div>
    </div>
  );
}

export function Trends() {
  const queryClient = useQueryClient();
  const { data: analysis, refetch: refetchAnalysis } = useLatestAnalysis();

  const onAnalysisComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["analysis", "latest"] });
    void refetchAnalysis();
  };

  const { messages, isStreaming, sendMessage } = useChat(SESSION_ID, onAnalysisComplete);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [selected, setSelected] = useState<string | null>(null);

  const hasMessages = messages.length > 0;
  const machines = extractMachinesFromAnalysis(analysis?.top_at_risk_machines);
  const hasContent = hasMessages || machines.length > 0;
  const topMachineId = selected ?? machines[0]?.machine_id ?? null;

  const { data: logsData } = useLogs({
    page: 1,
    page_size: 200,
    machine_id: topMachineId ?? undefined,
  });

  // Show flashcards for the last "analyze" response alongside prior analysis
  const sidebarMachines = useMemo(() => machines, [machines]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      className={cn(
        "transition-all duration-500 ease-in-out px-6",
        hasContent
          ? "py-6 max-w-7xl mx-auto"
          : "flex flex-col items-center justify-center min-h-[calc(100vh-3.5rem)]"
      )}
    >
      <div
        className={cn(
          "flex gap-6 w-full transition-all duration-500",
          hasContent ? "items-start" : "justify-center"
        )}
      >
        {/* Chat column */}
        <div
          className={cn(
            "flex flex-col transition-all duration-500",
            hasContent ? "flex-1 min-w-0" : "w-full max-w-2xl"
          )}
        >
          <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden flex flex-col">

            {/* Empty state */}
            {!hasMessages && (
              <div className="flex flex-col items-center justify-center py-14 gap-3 text-center px-6">
                <div className="w-11 h-11 rounded-full bg-gray-900 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">Fleet analyst ready</p>
                  <p className="text-xs text-gray-400 mt-1 max-w-xs leading-relaxed">
                    Run an analysis to identify at-risk machines, or ask a question about your fleet.
                  </p>
                </div>
                {analysis?.completed_at && (
                  <p className="text-xs text-gray-400">
                    Last analysis: {formatDate(analysis.completed_at)}
                    {analysis.model_used && <span className="ml-1">· {analysis.model_used}</span>}
                  </p>
                )}
              </div>
            )}

            {/* Message thread */}
            {hasMessages && (
              <div className="flex flex-col gap-5 p-5 max-h-[60vh] overflow-y-auto">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className="animate-message-in"
                    style={{ opacity: 0 }}
                  >
                    <MessageBubble msg={msg} />
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}

            <ChatInput
              onSend={(text) => sendMessage(text, false)}
              onAnalyze={() => sendMessage("", true)}
              isStreaming={isStreaming}
            />
          </div>

        </div>

        {/* Risk sidebar */}
        {sidebarMachines.length > 0 && (
          <RiskSidebar
            machines={sidebarMachines}
            selected={selected}
            onSelect={setSelected}
          />
        )}
      </div>

      {/* Sensor chart carousel */}
      {machines.length > 0 && topMachineId && (() => {
        const activeIndex = Math.max(0, machines.findIndex(m => m.machine_id === topMachineId));
        const handlePrev = () => setSelected(machines[(activeIndex - 1 + machines.length) % machines.length].machine_id);
        const handleNext = () => setSelected(machines[(activeIndex + 1) % machines.length].machine_id);
        return (
          <div className="mt-6 bg-white rounded-2xl border border-gray-200 p-5 animate-fade-in" style={{ opacity: 0 }}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-semibold text-gray-700">{topMachineId} — Sensor Trends</p>
                <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-3">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" />Error</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />Warning</span>
                </p>
              </div>
              {machines.length > 1 && (
                <div className="flex items-center gap-2">
                  <button onClick={handlePrev} className="w-7 h-7 rounded-full border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors">
                    <ChevronLeft className="w-4 h-4 text-gray-500" />
                  </button>
                  <div className="flex items-center gap-1.5">
                    {machines.map((m, i) => (
                      <button
                        key={m.machine_id}
                        onClick={() => setSelected(m.machine_id)}
                        className={cn("w-1.5 h-1.5 rounded-full transition-colors", i === activeIndex ? "bg-gray-900" : "bg-gray-300")}
                      />
                    ))}
                  </div>
                  <button onClick={handleNext} className="w-7 h-7 rounded-full border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors">
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              )}
            </div>
            <SensorChart logs={logsData?.items ?? []} machineId={topMachineId} />
          </div>
        );
      })()}
    </div>
  );
}
