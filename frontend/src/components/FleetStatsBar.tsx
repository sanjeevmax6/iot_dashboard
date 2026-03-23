import { AlertCircle, AlertTriangle, CheckCircle, Server } from "lucide-react";
import type { Machine } from "@/types";

interface Props {
  machines: Machine[];
  totalLogs: number;
}

export function FleetStatsBar({ machines, totalLogs }: Props) {
  const totalErrors = machines.reduce((s, m) => s + m.error_count, 0);
  const totalWarnings = machines.reduce((s, m) => s + m.warning_count, 0);

  const stats = [
    {
      label: "Machines",
      value: machines.length,
      icon: Server,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "Total Logs",
      value: totalLogs.toLocaleString(),
      icon: CheckCircle,
      color: "text-gray-600",
      bg: "bg-gray-50",
    },
    {
      label: "Errors",
      value: totalErrors,
      icon: AlertCircle,
      color: "text-red-600",
      bg: "bg-red-50",
    },
    {
      label: "Warnings",
      value: totalWarnings,
      icon: AlertTriangle,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {stats.map(({ label, value, icon: Icon, color, bg }) => (
        <div
          key={label}
          className="bg-white rounded-lg border border-gray-200 p-4 flex items-center gap-3"
        >
          <div className={`${bg} rounded-lg p-2`}>
            <Icon className={`w-5 h-5 ${color}`} />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
