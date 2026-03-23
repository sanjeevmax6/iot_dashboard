import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface Props {
  thoughts: string;
  isStreaming: boolean;
}

export function ThoughtsPanel({ thoughts, isStreaming }: Props) {
  const ref = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (ref.current && isStreaming) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [thoughts, isStreaming]);

  if (!thoughts) return null;

  return (
    <details
      open={isStreaming}
      className="group rounded-lg border border-gray-200 bg-gray-50 overflow-hidden mb-2"
    >
      <summary className="flex items-center gap-2 px-3 py-2 text-xs text-gray-500 cursor-pointer select-none list-none hover:bg-gray-100 transition-colors">
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full",
            isStreaming ? "bg-blue-500 animate-pulse" : "bg-gray-400"
          )}
        />
        {isStreaming ? "Thinking…" : "Thoughts"}
        <span className="ml-auto text-gray-400 group-open:rotate-180 transition-transform">
          ▾
        </span>
      </summary>
      <pre
        ref={ref}
        className="px-3 pb-3 text-xs text-gray-500 font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto"
      >
        {thoughts}
      </pre>
    </details>
  );
}
