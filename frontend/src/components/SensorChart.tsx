// Component that displays the time series graph of top risk machines
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDate } from "@/lib/utils";
import type { LogEntry } from "@/types";

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: { status: string };
}

interface Props {
  logs: LogEntry[];
  machineId: string;
}

// Placing this outside as each rerender might cause the dots to flicker, this makes it stable
function StatusDot({ cx, cy, payload }: DotProps) {
  if (!cx || !cy || !payload) return null;
  if (payload.status === "ERROR") {
    return <circle cx={cx} cy={cy} r={3.5} fill="#ef4444" stroke="white" strokeWidth={1.5} />;
  }
  if (payload.status === "WARNING") {
    return <circle cx={cx} cy={cy} r={3.5} fill="#f59e0b" stroke="white" strokeWidth={1.5} />;
  }
  return null;
}

export function SensorChart({ logs, machineId }: Props) {
  const data = [...logs]
    .filter((l) => l.machine_id === machineId)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((l) => ({
      time: formatDate(l.timestamp),
      temperature: l.temperature,
      vibration: l.vibration,
      status: l.status,
    }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-gray-400">
        No data for {machineId}
      </div>
    );
  }

  return (
    // Responsive cotnainer to render the smooth transition
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="time"
          tick={{ fontSize: 10, fill: "#9ca3af" }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          yAxisId="temp"
          orientation="left"
          tick={{ fontSize: 10, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          label={{ value: "°C", position: "insideTopLeft", fontSize: 10, fill: "#9ca3af" }}
        />
        <YAxis
          yAxisId="vib"
          orientation="right"
          tick={{ fontSize: 10, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          label={{ value: "vib", position: "insideTopRight", fontSize: 10, fill: "#9ca3af" }}
        />
        <Tooltip
          contentStyle={{ fontSize: 12, border: "1px solid #e5e7eb", borderRadius: 6 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          yAxisId="temp"
          type="monotone"
          dataKey="temperature"
          stroke="#3b82f6"
          strokeWidth={1.5}
          dot={<StatusDot />}
          activeDot={{ r: 4 }}
          name="Temperature (°C)"
        />
        <Line
          yAxisId="vib"
          type="monotone"
          dataKey="vibration"
          stroke="#f59e0b"
          strokeWidth={1.5}
          dot={<StatusDot />}
          activeDot={{ r: 4 }}
          name="Vibration"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
