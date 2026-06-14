import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

function formatXDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-xs text-gray-100 shadow-lg">
      <p className="text-gray-400 mb-1">{formatXDate(label)}</p>
      <p className="font-semibold text-green-400">
        {(payload[0].value || 0).toLocaleString()} views
      </p>
    </div>
  );
}

export default function StatsChart({ data = [] }) {
  return (
    <div style={{ height: 256 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="#374151" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatXDate}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            axisLine={{ stroke: "#374151" }}
            tickLine={false}
            dy={6}
          />
          <YAxis
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v)}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "#4b5563", strokeWidth: 1 }} />
          <Line
            type="monotone"
            dataKey="views"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#22c55e", stroke: "#166534" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
