"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

export interface ChartSpec {
  type: "bar" | "pie" | "line";
  title: string;
  labels: string[];
  data: number[];
  x_label?: string;
  y_label?: string;
}

const COLORS = [
  "#005288", "#1a4480", "#2672de", "#0076d6", "#97d4ea",
  "#00bde3", "#0081a1", "#336a90", "#3a7fc1", "#c9f0ff",
];

function truncate(str: string, max = 20) {
  return str.length > max ? str.slice(0, max) + "…" : str;
}

export function RecallChart({ spec }: { spec: ChartSpec }) {
  const chartData = spec.labels.map((label, i) => ({
    name: label,
    value: spec.data[i] ?? 0,
  }));

  return (
    <div
      style={{
        background: "#f0f4f8",
        border: "1px solid #dfe1e2",
        borderRadius: "6px",
        padding: "1rem",
        marginTop: "0.75rem",
      }}
    >
      <p
        style={{
          fontWeight: 700,
          fontSize: "0.875rem",
          color: "#1b1b1b",
          marginBottom: "0.75rem",
        }}
      >
        {spec.title}
      </p>

      {spec.type === "pie" ? (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${truncate(String(name ?? ""), 14)} ${((percent ?? 0) * 100).toFixed(0)}%`
              }
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => [Number(v ?? 0), "Recalls"]} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(220, chartData.length * 28)}>
          <BarChart
            data={chartData}
            layout={chartData.length > 6 ? "vertical" : "horizontal"}
            margin={{ top: 4, right: 20, left: 8, bottom: chartData.length > 6 ? 4 : 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#dfe1e2" />
            {chartData.length > 6 ? (
              <>
                <XAxis type="number" tick={{ fontSize: 11 }} label={spec.y_label ? { value: spec.y_label, position: "insideBottom", offset: -4, fontSize: 11 } : undefined} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => truncate(v, 18)}
                />
              </>
            ) : (
              <>
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => truncate(v, 14)}
                  label={spec.x_label ? { value: spec.x_label, position: "insideBottom", offset: -30, fontSize: 11 } : undefined}
                  interval={0}
                  angle={chartData.length > 4 ? -30 : 0}
                  textAnchor={chartData.length > 4 ? "end" : "middle"}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  label={spec.y_label ? { value: spec.y_label, angle: -90, position: "insideLeft", fontSize: 11 } : undefined}
                  allowDecimals={false}
                />
              </>
            )}
            <Tooltip
              formatter={(v) => [Number(v ?? 0), "Recalls"]}
              labelFormatter={(l) => String(l)}
            />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
