import { cn } from "@/lib/utils";
import type { MachineRisk } from "@/types";
import { RiskBadge } from "@/components/RiskBadge";

const scoreBarColor: Record<MachineRisk["risk_level"], string> = {
  high: "bg-red-500",
  medium: "bg-amber-400",
  low: "bg-green-500",
};

const cardBorder: Record<MachineRisk["risk_level"], string> = {
  high: "border-red-200 bg-red-50/40",
  medium: "border-amber-200 bg-amber-50/40",
  low: "border-green-200 bg-green-50/40",
};

interface Props {
  machine: MachineRisk;
  index: number;
}

export function AnalysisFlashcard({ machine, index }: Props) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 flex flex-col gap-3 animate-message-in",
        cardBorder[machine.risk_level]
      )}
      style={{ animationDelay: `${index * 180}ms`, opacity: 0 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-gray-900 text-sm">{machine.machine_id}</span>
          <RiskBadge level={machine.risk_level} />
        </div>
        <span className="text-xs text-gray-500 font-medium">
          Score {machine.risk_score.toFixed(2)}
        </span>
      </div>

      {/* Score bar */}
      <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", scoreBarColor[machine.risk_level])}
          style={{ width: `${machine.risk_score * 100}%` }}
        />
      </div>

      {/* Reason */}
      <p className="text-sm text-gray-700 leading-relaxed">{machine.reason}</p>

      {/* Sensors */}
      {machine.affected_sensors.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-gray-400 self-center">Sensors</span>
          {machine.affected_sensors.map((s) => (
            <span
              key={s}
              className="px-2 py-0.5 rounded-full bg-white border border-gray-200 text-xs text-gray-600"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Action */}
      <div className="flex items-start gap-2 pt-1 border-t border-gray-200/60">
        <span className="text-xs text-gray-400 mt-0.5 shrink-0">→</span>
        <p className="text-xs text-gray-700 font-medium">{machine.recommended_action}</p>
      </div>
    </div>
  );
}
