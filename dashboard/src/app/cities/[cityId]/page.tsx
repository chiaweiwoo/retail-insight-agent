export const dynamic = "force-dynamic";

import { Activity, Clock3, Target, Zap } from "lucide-react";
import SalesChart from "./SalesChart";
import { rca } from "@/lib/supabase";

export default async function CityOverview({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  const cityKey = Number(cityId);

  const [{ data: salesRows, error }, { data: goalRows }, { data: signalRows }] = await Promise.all([
    rca.from("sales").select("dt,total_sales").eq("city_id", cityKey).order("dt", { ascending: true }),
    rca.from("goals").select("dt,expected_sales").eq("city_id", cityKey).order("dt", { ascending: true }),
    rca.from("signals").select("dt,signal_label").eq("city_id", cityKey).order("dt", { ascending: true }),
  ]);

  if (error || !salesRows) {
    return <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-300">Error loading city data.</div>;
  }

  const sales = salesRows.map((row) => Number(row.total_sales || 0));
  const mean = sales.length ? sales.reduce((sum, value) => sum + value, 0) / sales.length : 0;
  const stddev = sales.length ? Math.sqrt(sales.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / sales.length) : 0;
  const goalMap = new Map((goalRows || []).map((row) => [row.dt, Number(row.expected_sales || 0)]));
  const signalMap = new Map((signalRows || []).map((row) => [row.dt, row.signal_label]));
  const chartData = salesRows.map((row) => ({
    date: row.dt,
    Sales: Number(row.total_sales || 0),
    Goal: goalMap.get(row.dt) || Number(row.total_sales || 0),
    Signal: signalMap.get(row.dt) || null,
  }));
  const triggeredCount = chartData.filter((row) => row.Signal === "drop" || row.Signal === "lift").length;
  const triggeredDates = chartData.filter((row) => row.Signal === "drop" || row.Signal === "lift");

  return (
    <div className="space-y-8">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <div className="glass-card rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-3 text-slate-400">
            <Target size={18} className="text-teal-400" />
            <span className="text-sm font-medium">Average Sales</span>
          </div>
          <div className="text-3xl font-bold text-white">{Math.round(mean).toLocaleString()}</div>
          <div className="mt-2 text-xs text-slate-500">Normalized sales amount</div>
        </div>
        <div className="glass-card rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-3 text-slate-400">
            <Activity size={18} className="text-amber-400" />
            <span className="text-sm font-medium">Volatility</span>
          </div>
          <div className="text-3xl font-bold text-white">{Math.round(stddev).toLocaleString()}</div>
          <div className="mt-2 text-xs text-slate-500">Simple day-to-day spread</div>
        </div>
        <div className="glass-card rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-3 text-slate-400">
            <Zap size={18} className="text-rose-400" />
            <span className="text-sm font-medium">Signals</span>
          </div>
          <div className="text-3xl font-bold text-white">{triggeredCount}</div>
          <div className="mt-2 text-xs text-slate-500">Drop or lift markers in this window</div>
        </div>
        <div className="glass-card rounded-2xl p-5">
          <div className="mb-3 flex items-center gap-3 text-slate-400">
            <Clock3 size={18} className="text-indigo-400" />
            <span className="text-sm font-medium">Workflow</span>
          </div>
          <div className="text-xl font-bold text-white">Manual RCA</div>
          <div className="mt-2 text-xs text-slate-500">Use `rca run` to create or refresh the LLM result</div>
        </div>
      </div>

      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white">Actual Sales vs Business Goal (synthetic)</h2>
        <p className="mt-2 text-sm text-slate-400">Markers show city/date signals. Click a red or green marker to jump to the RCA result for that day.</p>
        <SalesChart cityId={cityId} data={chartData} />
        <div className="mt-5">
          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Triggered Dates</div>
          {triggeredDates.length === 0 ? (
            <p className="text-sm text-slate-500">No drop or lift dates found in the current signal table for this city.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {triggeredDates.map((row) => (
                <a
                  key={row.date}
                  href={`/cities/${cityId}/rca?date=${row.date}`}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                    row.Signal === "drop"
                      ? "border-rose-500/25 bg-rose-500/10 text-rose-300 hover:bg-rose-500/15"
                      : "border-emerald-500/25 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/15"
                  }`}
                >
                  {row.date}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
