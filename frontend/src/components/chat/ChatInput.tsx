import { ArrowRight, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  onSend: (text: string) => void;
  onAnalyze: () => void;
  onClearAnalysis?: () => void;
  hasAnalysis?: boolean;
  isStreaming: boolean;
}

export function ChatInput({ onSend, onAnalyze, onClearAnalysis, hasAnalysis, isStreaming }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const text = value.trim();
    if (!text || isStreaming) return;
    setValue("");
    onSend(text);
    ref.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="border-t border-gray-100 p-3 flex flex-col gap-2">
      <div className="flex items-end gap-2">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={isStreaming}
          rows={1}
          placeholder={isStreaming ? "Analyzing…" : "Ask a follow-up question…"}
          className={cn(
            "flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm",
            "placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-300",
            "disabled:bg-gray-50 disabled:text-gray-400 max-h-32 overflow-y-auto"
          )}
          style={{ height: "36px" }}
          onInput={(e) => {
            const t = e.currentTarget;
            t.style.height = "36px";
            t.style.height = `${Math.min(t.scrollHeight, 128)}px`;
          }}
        />
        <button
          onClick={submit}
          disabled={!value.trim() || isStreaming}
          className={cn(
            "p-2 rounded-xl transition-colors shrink-0",
            value.trim() && !isStreaming
              ? "bg-gray-900 text-white hover:bg-gray-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          )}
        >
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center justify-center gap-2">
        <button
          onClick={onAnalyze}
          disabled={isStreaming}
          className={cn(
            "flex items-center justify-center gap-1.5 w-[38%] py-1.5 rounded-xl text-xs font-medium transition-colors border",
            isStreaming
              ? "border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
              : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
          )}
        >
          <Sparkles className="w-3.5 h-3.5" />
          {isStreaming ? "Analyzing fleet…" : "Analyze fleet health"}
        </button>

        {hasAnalysis && (
          <button
            onClick={onClearAnalysis}
            disabled={isStreaming}
            className={cn(
              "flex items-center justify-center gap-1.5 w-[38%] py-1.5 rounded-xl text-xs font-medium transition-colors border",
              isStreaming
                ? "border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
                : "border-red-200 bg-red-50 text-red-600 hover:bg-red-100"
            )}
          >
            <X className="w-3.5 h-3.5" />
            Clear analysis
          </button>
        )}
      </div>
    </div>
  );
}
