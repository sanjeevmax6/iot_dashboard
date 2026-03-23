import { Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  role: "user" | "ai";
  children: React.ReactNode;
  delay?: number;
  className?: string;
}

export function ChatBubble({ role, children, delay = 0, className }: Props) {
  if (role === "user") {
    return (
      <div
        className={cn("flex justify-end animate-message-in", className)}
        style={{ animationDelay: `${delay}ms`, opacity: 0 }}
      >
        <div className="bg-blue-600 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xs">
          {children}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("flex items-start gap-2.5 animate-message-in", className)}
      style={{ animationDelay: `${delay}ms`, opacity: 0 }}
    >
      <div className="w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center shrink-0 mt-0.5">
        <Bot className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
