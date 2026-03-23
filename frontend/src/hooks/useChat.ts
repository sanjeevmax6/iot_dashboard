import { useCallback, useRef, useState } from "react";
import { api } from "@/api/client";

export interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  thoughts: string;
  isStreaming: boolean;
}

function uid() {
  return Math.random().toString(36).slice(2);
}

// Detect "top N" intent in a user message, e.g. "give me top 5", "top-3 machines", "show top 10"
// Returns the requested count, 0 for "all", or null if no analysis intent found.
function parseAnalysisIntent(text: string): number | null {
  const topN = text.match(/\btop[\s-]?(\d+)\b/i);
  if (topN) return parseInt(topN[1], 10);
  if (/\b(all|every)\b.{0,30}\b(machine|at[\s-]?risk)\b/i.test(text)) return 0;
  return null;
}

export function useChat(sessionId: string, onAnalysisComplete?: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string, triggerAnalysis = false) => {
      if (isStreaming) return;

      // Detect "top N" / "all machines" intent in plain chat messages
      let requestedCount: number | null | undefined;
      if (!triggerAnalysis && text) {
        const intent = parseAnalysisIntent(text);
        if (intent !== null) {
          triggerAnalysis = true;
          requestedCount = intent === 0 ? 0 : intent;
        }
      }

      // Add user bubble
      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: triggerAnalysis && !text ? "Analyze fleet health" : text,
        thoughts: "",
        isStreaming: false,
      };

      // Placeholder AI bubble
      const aiId = uid();
      const aiMsg: ChatMessage = {
        id: aiId,
        role: "ai",
        content: "",
        thoughts: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);
      setIsStreaming(true);

      try {
        const response = await api.chat.stream({
          message: text,
          session_id: sessionId,
          trigger_analysis: triggerAnalysis,
          requested_count: requestedCount,
        });

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let thoughtsBuffer = "";
        let finalMessage = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const event = JSON.parse(line.slice(6)) as Record<string, unknown>;

            if (event.type === "thinking_token") {
              thoughtsBuffer += event.content as string;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId ? { ...m, thoughts: thoughtsBuffer } : m
                )
              );
            } else if (event.type === "done") {
              finalMessage = event.message as string;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId
                    ? { ...m, content: finalMessage, isStreaming: false }
                    : m
                )
              );
              if (triggerAnalysis) onAnalysisComplete?.();
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId
                    ? { ...m, content: `Error: ${event.message as string}`, isStreaming: false }
                    : m
                )
              );
            }
          }
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.isStreaming ? { ...m, content: "Connection error.", isStreaming: false } : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, sessionId]
  );

  return { messages, isStreaming, sendMessage };
}
