import Link from "next/link";
import { ArrowRight, Info } from "lucide-react";
import { rca } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function CitiesPage() {
  const [{ data: signalRows, error }, { data: salesRows }] = await Promise.all([
    rca.from("signals").select("city_id,dt,signal_label,total_sales,expected_sales,deviation_pct").order("dt", { ascending: true }),
    rca.from("sales").select("city_id,dt,total_sales").order("dt", { ascending: true }),
  ]);

  if (error) {
    return <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-300">{error.message}</div>;
  }

  const rows = signalRows || [];
  const sales = salesRows || [];
  const allDates = Array.from(new Set(rows.map((row) => row.dt))).sort();
  const cityAverages = new Map<number, number>();
  const cityTotals = new Map<number, number>();
  const cityCounts = new Map<number, number>();
  for (const row of sales) {
    cityTotals.set(row.city_id, (cityTotals.get(row.city_id) || 0) + Number(row.total_sales || 0));
    cityCounts.set(row.city_id, (cityCounts.get(row.city_id) || 0) + 1);
  }
  for (const [cityId, total] of cityTotals.entries()) {
    cityAverages.set(cityId, total / Math.max(cityCounts.get(cityId) || 1, 1));
  }

  const cityIds = Array.from(new Set(rows.map((row) => row.city_id))).sort((a, b) => (cityAverages.get(b) || 0) - (cityAverages.get(a) || 0));
  const grid = new Map<string, { signal_label: string; deviation_pct: number | null }>();
  for (const row of rows) {
    grid.set(`${row.city_id}:${row.dt}`, { signal_label: row.signal_label, deviation_pct: row.deviation_pct });
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Signals Heatmap</h1>
          <p className="flex items-center gap-2 text-sm leading-relaxed text-slate-400">
            <span>City versus date screening against the synthetic business goal.</span>
            <span className="group relative inline-flex cursor-help items-center justify-center">
              <Info size={16} className="text-indigo-400" />
              <span className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-64 -translate-x-1/2 rounded-xl border border-slate-700 bg-slate-900 p-3 text-xs text-slate-200 opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
                Synthetic business goals come from recent history and same-weekday baselines. The LLM can later challenge the signal, but the heatmap stays fast and simple.
              </span>
            </span>
          </p>
        </div>
      </div>

      <div className="glass-panel overflow-x-auto rounded-2xl border border-white/5 bg-slate-900/50">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr>
              <th className="sticky left-0 z-20 min-w-[150px] border-b border-r border-white/10 bg-slate-900/95 p-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                City / Avg
              </th>
              {allDates.map((date) => (
                <th key={date} className="min-w-[34px] border-b border-white/10 p-1 text-center text-[10px] font-medium text-slate-500" title={date}>
                  {new Date(date).getDate()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cityIds.map((cityId) => (
              <tr key={cityId} className="group hover:bg-white/[0.02]">
                <td className="sticky left-0 z-10 border-b border-r border-white/10 bg-slate-900/95 p-3 group-hover:bg-slate-800/95">
                  <div className="flex items-center justify-between gap-3">
                    <Link href={`/cities/${cityId}`} className="flex items-center gap-1 text-sm font-medium text-indigo-300 hover:text-indigo-200">
                      <span>City {cityId}</span>
                      <ArrowRight size={12} />
                    </Link>
                    <span className="text-[10px] font-medium text-slate-500">{Math.round(cityAverages.get(cityId) || 0).toLocaleString()}</span>
                  </div>
                </td>
                {allDates.map((date) => {
                  const cell = grid.get(`${cityId}:${date}`);
                  const signal = cell?.signal_label || "neutral";
                  const deviation = cell?.deviation_pct ?? null;
                  const tone =
                    signal === "drop"
                      ? "bg-rose-500/15 text-rose-300"
                      : signal === "lift"
                        ? "bg-emerald-500/15 text-emerald-300"
                        : "bg-white/[0.03] text-slate-500";
                  return (
                    <td key={date} className="border-b border-white/5 p-[1px] text-center" title={`${date} | ${signal}${deviation !== null ? ` | ${deviation.toFixed(1)}%` : ""}`}>
                      <div className={`flex h-full w-full items-center justify-center rounded-sm py-1.5 text-[9px] font-semibold ${tone}`}>
                        {deviation === null ? "?" : `${deviation > 0 ? "+" : ""}${Math.round(deviation)}`}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
