import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import type { LogEntry, Machine } from "@/types";

const statusStyles = {
  OPERATIONAL: "bg-green-50 text-green-700",
  WARNING: "bg-amber-50 text-amber-700",
  ERROR: "bg-red-50 text-red-700",
};

interface Props {
  logs: LogEntry[];
  total: number;
  page: number;
  pages: number;
  machines: Machine[];
  filters: { machine_id: string; status: string };
  onPageChange: (p: number) => void;
  onFilterChange: (key: "machine_id" | "status", value: string) => void;
}

export function LogsTable({
  logs,
  total,
  page,
  pages,
  machines,
  filters,
  onPageChange,
  onFilterChange,
}: Props) {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Filters */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
        <span className="text-sm text-gray-500">{total.toLocaleString()} records</span>
        <div className="flex gap-2 ml-auto">
          <select
            className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={filters.machine_id}
            onChange={(e) => onFilterChange("machine_id", e.target.value)}
          >
            <option value="">All Machines</option>
            {machines.map((m) => (
              <option key={m.machine_id} value={m.machine_id}>
                {m.machine_id}
              </option>
            ))}
          </select>
          <select
            className="text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={filters.status}
            onChange={(e) => onFilterChange("status", e.target.value)}
          >
            <option value="">All Status</option>
            <option value="operational">Operational</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">Timestamp</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">Machine</th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500">Temp (°C)</th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500">Vibration</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-gray-400 text-sm">
                  No logs found. Ingest a CSV to get started.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-gray-500 font-mono text-xs">
                    {formatDate(log.timestamp)}
                  </td>
                  <td className="px-4 py-2.5 font-medium text-gray-900">{log.machine_id}</td>
                  <td className="px-4 py-2.5 text-right text-gray-700">
                    {log.temperature.toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-700">
                    {log.vibration.toFixed(3)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                        statusStyles[log.status]
                      )}
                    >
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <span className="text-sm text-gray-500">
            Page {page} of {pages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1}
              className="p-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page === pages}
              className="p-1.5 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
