"use client";

import { useRouter } from "next/navigation";
import { Area, AreaChart, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format } from "date-fns";

interface ChartData {
  date: string;
  Sales: number;
  Goal: number;
  Signal: string | null;
}

export default function SalesChart({ cityId, data }: { cityId: string; data: ChartData[] }) {
  const router = useRouter();
  const triggeredPoints = data.filter((row) => row.Signal === "drop" || row.Signal === "lift");

  return (
    <div className="mt-4 h-[360px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0f766e" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            dy={10}
            minTickGap={30}
            tick={{ fill: "#64748b", fontSize: 12 }}
            tickFormatter={(value) => format(new Date(value), "MMM d")}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            dx={-10}
            tick={{ fill: "#64748b", fontSize: 12 }}
            tickFormatter={(value) => Math.round(value).toLocaleString()}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const signal = payload[0].payload.Signal;
              return (
                <div className="rounded-xl border border-white/10 bg-[#0F0F12]/90 p-3 shadow-xl backdrop-blur-xl">
                  <p className="mb-1 text-xs font-medium text-slate-400">{label}</p>
                  <p className="text-sm font-semibold text-white">Sales: {Math.round(Number(payload.find((entry) => entry.dataKey === "Sales")?.value)).toLocaleString()}</p>
                  <p className="mt-1 text-sm font-semibold text-slate-300">Goal: {Math.round(Number(payload.find((entry) => entry.dataKey === "Goal")?.value)).toLocaleString()}</p>
                  {signal && <p className="mt-2 text-xs font-medium text-slate-400">Click the red or green marker to open the RCA result.</p>}
                </div>
              );
            }}
          />
          <Area type="monotone" dataKey="Goal" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 4" fill="none" activeDot={false} />
          <Area type="monotone" dataKey="Sales" stroke="#0f766e" strokeWidth={2} fill="url(#salesFill)" activeDot={{ r: 5, fill: "#0f766e", stroke: "#020617", strokeWidth: 2 }} />
          {triggeredPoints.map((entry) => (
            <ReferenceDot
              key={entry.date}
              x={entry.date}
              y={entry.Sales}
              r={6}
              fill={entry.Signal === "drop" ? "#e11d48" : "#16a34a"}
              stroke="#020617"
              strokeWidth={2}
              ifOverflow="visible"
              className="cursor-pointer"
              onClick={() => router.push(`/cities/${cityId}/rca?date=${entry.date}`)}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
