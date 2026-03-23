import { cn } from "@/lib/utils";
import type { MachineRisk } from "@/types";
import { RiskBadge } from "@/components/RiskBadge";

const dotColor: Record<MachineRisk["risk_level"], string> = {
  high: "bg-red-500",
  medium: "bg-amber-400",
  low: "bg-green-500",
};

interface Props {
  machines: MachineRisk[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function RiskSidebar({ machines, selected, onSelect }: Props) {
  return (
    <div className="w-64 shrink-0 flex flex-col gap-3 animate-slide-in-right max-h-[calc(60vh+theme(spacing.20))]" style={{ opacity: 0 }}>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest px-1 shrink-0">
        Top at-risk
      </p>
      <div className="flex flex-col gap-3 overflow-y-auto pr-1">
      {machines.map((m) => (
        <button
          key={m.machine_id}
          onClick={() => onSelect(m.machine_id)}
          className={cn(
            "w-full text-left rounded-xl border p-3.5 flex flex-col gap-2.5 transition-all",
            selected === m.machine_id
              ? "border-gray-900 bg-white shadow-sm"
              : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={cn("w-2 h-2 rounded-full shrink-0", dotColor[m.risk_level])} />
              <span className="font-semibold text-gray-900 text-sm">{m.machine_id}</span>
            </div>
            <RiskBadge level={m.risk_level} />
          </div>
          <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full", dotColor[m.risk_level])}
              style={{ width: `${m.risk_score * 100}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 line-clamp-2">{m.reason}</p>
        </button>
      ))}
      </div>
    </div>
  );
}
