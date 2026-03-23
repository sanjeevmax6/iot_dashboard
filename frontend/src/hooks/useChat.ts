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

export function useChat(sessionId: string, onAnalysisComplete?: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string, triggerAnalysis = false) => {
      if (isStreaming) return;

      // Add user bubble
      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: triggerAnalysis ? "Analyze fleet health" : text,
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
