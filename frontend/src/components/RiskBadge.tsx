import { cn } from "@/lib/utils";
import type { MachineRisk } from "@/types";

const styles: Record<MachineRisk["risk_level"], string> = {
  high: "bg-red-50 text-red-700 border-red-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-green-50 text-green-700 border-green-200",
};

interface Props {
  level: MachineRisk["risk_level"];
}

export function RiskBadge({ level }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border uppercase tracking-wide",
        styles[level]
      )}
    >
      {level}
    </span>
  );
}
