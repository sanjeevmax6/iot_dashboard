import { cn } from "@/lib/utils";
import type { MachineRisk } from "@/types";
import { RiskBadge } from "./RiskBadge";

const borderStyles: Record<MachineRisk["risk_level"], string> = {
  high: "border-red-200 bg-red-50/30",
  medium: "border-amber-200 bg-amber-50/30",
  low: "border-green-200 bg-green-50/30",
};

interface Props {
  machine: MachineRisk;
}

export function MachineHealthCard({ machine }: Props) {
  return (
    <div
      className={cn(
        "rounded-lg border p-5 flex flex-col gap-3",
        borderStyles[machine.risk_level]
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-gray-500 font-medium">Machine</p>
          <p className="text-lg font-bold text-gray-900">{machine.machine_id}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <RiskBadge level={machine.risk_level} />
          <p className="text-xs text-gray-500">
            Score: <span className="font-semibold text-gray-700">{machine.risk_score.toFixed(2)}</span>
          </p>
        </div>
      </div>

      <p className="text-sm text-gray-700">{machine.reason}</p>

      {machine.affected_sensors.length > 0 && (
        <div className="flex gap-1.5 flex-wrap">
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

      <div className="pt-1 border-t border-gray-200/60">
        <p className="text-xs text-gray-500 font-medium mb-0.5">Recommended action</p>
        <p className="text-sm text-gray-800">{machine.recommended_action}</p>
      </div>
    </div>
  );
}
