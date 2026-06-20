"use client";

import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceDot } from "recharts";
import { format } from "date-fns";

interface ChartData {
  date: string;
  Sales: number;
  Forecast: number;
  Trigger: string | null;
}

export default function SalesChart({ data }: { data: ChartData[] }) {
  // Extract triggered points for ReferenceDots
  const triggeredPoints = data.filter((d) => d.Trigger !== null);

  return (
    <div className="h-[350px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
          <XAxis 
            dataKey="date" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#64748b", fontSize: 12 }}
            tickFormatter={(val) => {
              try {
                return format(new Date(val), "MMM d");
              } catch {
                return val;
              }
            }}
            dy={10}
            minTickGap={30}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: "#64748b", fontSize: 12 }} 
            tickFormatter={(val) => Math.round(val).toLocaleString()}
            dx={-10}
          />
          <Tooltip 
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const isTrigger = payload[0].payload.Trigger;
                return (
                  <div className="bg-[#0F0F12]/90 backdrop-blur-xl border border-white/10 p-3 rounded-xl shadow-xl">
                    <p className="text-slate-400 text-xs mb-1 font-medium">{label}</p>
                    <p className="text-white font-semibold flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                      <span>{Math.round(Number(payload.find(p => p.dataKey === 'Sales')?.value)).toLocaleString()} Sales</span>
                    </p>
                    <p className="text-slate-300 font-semibold flex items-center space-x-2 mt-1">
                      <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                      <span>{Math.round(Number(payload.find(p => p.dataKey === 'Forecast')?.value)).toLocaleString()} Forecast</span>
                    </p>
                    {isTrigger && (
                      <div className={`mt-2 text-xs font-medium px-2 py-1 rounded border inline-block ${
                        isTrigger === "drop" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      }`}>
                        Agent RCA: {isTrigger.toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              }
              return null;
            }}
          />
          <Area 
            type="monotone" 
            dataKey="Forecast" 
            stroke="#64748b" 
            strokeWidth={1.5}
            strokeDasharray="3 3"
            fill="none" 
            activeDot={false}
          />
          <Area 
            type="monotone" 
            dataKey="Sales" 
            stroke="#6366f1" 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorSales)" 
            activeDot={{ r: 6, fill: "#6366f1", stroke: "#0A0A0B", strokeWidth: 2 }}
          />
          
          {/* Render markers for triggered days */}
          {triggeredPoints.map((entry, index) => (
            <ReferenceDot 
              key={`dot-${index}`}
              x={entry.date} 
              y={entry.Sales} 
              r={5} 
              fill={entry.Trigger === "drop" ? "#f43f5e" : "#10b981"} 
              stroke="#0A0A0B"
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
