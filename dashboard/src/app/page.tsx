import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { Info, ArrowRight } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function StoresPage() {
  // Fetch city normals for sorting and axis labels
  const { data: normals, error: normalsError } = await supabase
    .from("rca_city_normals")
    .select("city_id, density_tier, avg_sale, store_count")
    .order("avg_sale", { ascending: false });

  if (normalsError) {
    return (
      <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20 glass-panel">
        <h2 className="text-lg font-semibold">Database Connection Error</h2>
        <p className="mt-2 opacity-80">{normalsError.message}</p>
      </div>
    );
  }

  // Fetch the latest 21 days of data to compute 7-day trailing averages for the last 14 days
  const { data: seriesData, error: seriesError } = await supabase
    .from("rca_city_series")
    .select("city_id, dt, total_sales")
    .order("dt", { ascending: false })
    .limit(18 * 21); // 18 cities * 21 days

  if (seriesError) {
    return <div>Error loading series data: {seriesError.message}</div>;
  }

  // Get unique dates sorted descending
  const allDates = Array.from(new Set(seriesData?.map((d) => d.dt) || []))
    .sort((a, b) => b.localeCompare(a));
  
  // We want to show the last 14 days
  const displayDates = allDates.slice(0, 14).reverse();

  // Group by city_id
  const citySeries = seriesData?.reduce((acc: any, row: any) => {
    if (!acc[row.city_id]) acc[row.city_id] = {};
    acc[row.city_id][row.dt] = row.total_sales;
    return acc;
  }, {});

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Fleet Overview (City Level)</h1>
          <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed flex items-center space-x-2">
            <span>Heatmap of regional performance across the last 14 days.</span>
            <span className="group relative cursor-help inline-flex items-center justify-center">
              <Info size={16} className="text-indigo-400" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 text-xs text-slate-200 rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 border border-slate-700">
                <strong className="text-white block mb-1">RCA Triggers:</strong>
                <span className="text-rose-400 font-semibold">Drop:</span> Sales ≤ -15% vs 7-day trailing avg<br/>
                <span className="text-emerald-400 font-semibold">Lift:</span> Sales ≥ +15% vs 7-day trailing avg
              </div>
            </span>
          </p>
        </div>
      </div>

      <div className="glass-panel overflow-x-auto rounded-2xl border border-white/5 bg-slate-900/50 relative">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-20 bg-slate-900/90 backdrop-blur border-b border-r border-white/10 p-4 min-w-[200px]">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">City / Avg Volume</div>
              </th>
              {displayDates.map((date) => {
                const d = new Date(date);
                return (
                  <th key={date} className="border-b border-white/10 p-3 min-w-[120px] text-center">
                    <div className="text-xs font-medium text-slate-300">{d.toLocaleDateString('en-US', { weekday: 'short' })}</div>
                    <div className="text-xs text-slate-500">{d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {normals?.map((city: any) => {
              const rowData = citySeries[city.city_id] || {};
              
              return (
                <tr key={city.city_id} className="group hover:bg-white/[0.02] transition-colors">
                  <td className="sticky left-0 z-10 bg-slate-900/90 group-hover:bg-slate-800/90 backdrop-blur border-b border-r border-white/10 p-4">
                    <div className="flex flex-col">
                      <Link href={`/cities/${city.city_id}`} className="text-sm font-medium text-indigo-300 hover:text-indigo-200 hover:underline flex items-center space-x-1">
                        <span>City {city.city_id}</span>
                        <ArrowRight size={12} />
                      </Link>
                      <div className="text-xs text-slate-500 mt-0.5">
                        Vol: {Math.round(city.avg_sale).toLocaleString()} | {city.store_count} stores
                      </div>
                    </div>
                  </td>
                  
                  {displayDates.map((date, idx) => {
                    const currentSales = rowData[date] || 0;
                    
                    // compute 7 day trailing avg manually for the heatmap logic
                    const dateIdx = allDates.indexOf(date);
                    let trailingAvg = 0;
                    let pctChange = 0;
                    if (dateIdx >= 0 && dateIdx + 7 < allDates.length) {
                      let sum = 0;
                      let count = 0;
                      for (let i = 1; i <= 7; i++) {
                        const priorDate = allDates[dateIdx + i];
                        if (rowData[priorDate]) {
                          sum += rowData[priorDate];
                          count++;
                        }
                      }
                      if (count > 0) {
                        trailingAvg = sum / count;
                        pctChange = (currentSales - trailingAvg) / trailingAvg;
                      }
                    }

                    const pctStr = (pctChange > 0 ? '+' : '') + (pctChange * 100).toFixed(1) + '%';
                    const isDrop = pctChange <= -0.15;
                    const isLift = pctChange >= 0.15;

                    let cellBg = '';
                    let textClass = 'text-slate-400';
                    if (isDrop) {
                      cellBg = 'bg-rose-500/10 border-rose-500/30';
                      textClass = 'text-rose-400';
                    } else if (isLift) {
                      cellBg = 'bg-emerald-500/10 border-emerald-500/30';
                      textClass = 'text-emerald-400';
                    }

                    return (
                      <td key={date} className="border-b border-white/5 p-2 text-center">
                        <div className={`mx-auto w-full h-full min-h-[3.5rem] rounded flex flex-col justify-center items-center border border-transparent transition-colors ${cellBg}`}>
                          {currentSales > 0 ? (
                            <>
                              <div className="text-xs font-medium text-slate-300">
                                {Math.round(currentSales).toLocaleString()}
                              </div>
                              {trailingAvg > 0 && (
                                <div className={`text-[10px] font-semibold ${textClass}`}>
                                  {pctStr}
                                </div>
                              )}
                            </>
                          ) : (
                            <span className="text-xs text-slate-600">-</span>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
