import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { Info, ArrowRight } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function CitiesPage() {
  // Fetch city normals for sorting and axis labels
  const { data: normals, error: normalsError } = await supabase
    .from("rca_city_normals")
    .select("city_id, density_tier, avg_sale")
    .order("avg_sale", { ascending: false });

  if (normalsError) {
    return (
      <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20 glass-panel">
        <h2 className="text-lg font-semibold">Database Connection Error</h2>
        <p className="mt-2 opacity-80">{normalsError.message}</p>
      </div>
    );
  }

  // 2. Fetch Sales Series
  const { data: seriesData, error: seriesError } = await supabase
    .from("rca_city_series")
    .select("city_id, dt, total_sales")
    .order("dt", { ascending: true });

  // 3. Fetch Finance Forecast
  const { data: forecastData } = await supabase
    .from("rca_finance_forecast")
    .select("city_id, dt, forecast_sales")
    .order("dt", { ascending: true });

  // Group forecast by city_id
  const cityForecast = forecastData?.reduce((acc: any, row: any) => {
    if (!acc[row.city_id]) acc[row.city_id] = {};
    acc[row.city_id][row.dt] = row.forecast_sales;
    return acc;
  }, {});

  if (seriesError) {
    return <div>Error loading series data: {seriesError.message}</div>;
  }

  // Get unique dates sorted descending
  const allDates = Array.from(new Set(seriesData?.map((d) => d.dt) || []))
    .sort((a, b) => b.localeCompare(a));
  
  // We want to show the full 90-day span
  const displayDates = allDates.slice(0, 90).reverse();
  const totalDays = displayDates.length;

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
            <span>Heatmap of regional performance across the last 90 days. Scroll horizontally.</span>
            <span className="group relative cursor-help inline-flex items-center justify-center">
              <Info size={16} className="text-indigo-400" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 text-xs text-slate-200 rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 border border-slate-700">
                <p className="text-slate-300 block mb-2">We compare actual sales against the Corporate Finance S&OP Forecast.</p>
                <strong className="text-white block mb-1">RCA Triggers:</strong>
                <span className="text-rose-400 font-semibold">Drop:</span> Sales ≤ -10% vs Finance Forecast<br/>
                <span className="text-emerald-400 font-semibold">Lift:</span> Sales ≥ +25% vs Finance Forecast
              </div>
            </span>
          </p>
        </div>
      </div>

      <div className="glass-panel overflow-x-auto overscroll-x-none rounded-2xl border border-white/5 bg-slate-900/50 relative">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-20 bg-slate-900/90 backdrop-blur border-b border-r border-white/10 p-3 min-w-[140px]">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">City / Avg Vol</div>
              </th>
              {displayDates.map((date) => {
                const d = new Date(date);
                const isMonday = d.getDay() === 1;
                const borderLeft = isMonday ? "border-l-2 border-l-white/20" : "border-l border-l-transparent";
                return (
                  <th key={date} className={`border-b border-white/10 p-1 min-w-[32px] text-center ${borderLeft}`} title={date}>
                    <div className="text-[9px] font-medium text-slate-500">{d.getDate()}</div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {normals?.map((city: any) => {
              const rowData = citySeries[city.city_id] || {};
              
              const sparklineData = displayDates.map((date) => {
                const currentSales = rowData[date] || 0;
                const forecastSales = cityForecast?.[city.city_id]?.[date] || currentSales;
                
                let pctChange = 0;
                if (forecastSales > 0) {
                  pctChange = (currentSales - forecastSales) / forecastSales;
                }
                
                const isDrop = pctChange <= -0.10;
                const isLift = pctChange >= 0.25;
                return { date, currentSales, forecastSales, pctChange, isDrop, isLift };
              });

              const minSales = Math.min(...sparklineData.map(d => Math.min(d.currentSales, d.forecastSales)));
              const maxSales = Math.max(...sparklineData.map(d => Math.max(d.currentSales, d.forecastSales)));
              const salesRange = (maxSales - minSales) || 1;

              const pointsActual = sparklineData.map((d, i) => `${i * 4},${14 - ((d.currentSales - minSales) / salesRange) * 14}`).join(' ');
              const pointsForecast = sparklineData.map((d, i) => `${i * 4},${14 - ((d.forecastSales - minSales) / salesRange) * 14}`).join(' ');

              return (
                <tr key={city.city_id} className="group hover:bg-white/[0.02] transition-colors">
                  <td className="sticky left-0 z-10 bg-slate-900/90 group-hover:bg-slate-800/90 backdrop-blur border-b border-r border-white/10 p-3">
                    <div className="flex flex-col space-y-2">
                      <div className="flex items-center justify-between">
                        <Link href={`/cities/${city.city_id}`} className="text-sm font-medium text-indigo-300 hover:text-indigo-200 hover:underline flex items-center space-x-1">
                          <span>City {city.city_id}</span>
                          <ArrowRight size={12} />
                        </Link>
                        <div className="text-[10px] text-slate-500 font-medium">
                          {Math.round(city.avg_sale / 1000)}k
                        </div>
                      </div>
                      <div className="w-full shrink-0 flex items-center pr-2">
                        <svg width="100%" height="16" viewBox={`0 0 ${totalDays * 4} 16`} preserveAspectRatio="none" className="overflow-visible">
                          <polyline fill="none" stroke="#64748b" strokeWidth="1" strokeDasharray="2 2" points={pointsForecast} opacity="0.6" />
                          <polyline fill="none" stroke="#6366f1" strokeWidth="1.5" points={pointsActual} />
                          {sparklineData.map((d, i) => {
                            if (!d.isDrop && !d.isLift) return null;
                            const x = i * 4;
                            const y = 14 - ((d.currentSales - minSales) / salesRange) * 14;
                            return <circle key={i} cx={x} cy={y} r="2.5" fill={d.isDrop ? "#f43f5e" : "#10b981"} />;
                          })}
                        </svg>
                      </div>
                    </div>
                  </td>
                  
                  {sparklineData.map((cell) => {
                    const d = new Date(cell.date);
                    const isMonday = d.getDay() === 1;
                    const borderLeft = isMonday ? "border-l-2 border-l-white/20" : "border-l border-l-transparent";
                    const pctStr = (cell.pctChange > 0 ? '+' : '') + (cell.pctChange * 100).toFixed(1) + '%';
                    
                    let cellBg = '';
                    let textClass = 'text-slate-400';
                    if (cell.isDrop) {
                      cellBg = 'bg-rose-500/10 border-rose-500/30';
                      textClass = 'text-rose-400';
                    } else if (cell.isLift) {
                      cellBg = 'bg-emerald-500/10 border-emerald-500/30';
                      textClass = 'text-emerald-400';
                    }

                    return (
                      <td key={cell.date} className={`border-b border-white/5 p-[1px] text-center ${borderLeft}`} title={`${cell.date} | Actual: ${Math.round(cell.currentSales).toLocaleString()} | Forecast: ${Math.round(cell.forecastSales).toLocaleString()} | Error: ${pctStr}`}>
                        <div className={`mx-auto w-full h-full py-1.5 rounded-sm flex items-center justify-center transition-colors ${cellBg}`}>
                          {cell.currentSales > 0 && cell.forecastSales > 0 ? (
                            <span className={`text-[9px] font-bold tracking-tighter ${textClass}`}>
                              {cell.pctChange > 0 ? '+' : ''}{(cell.pctChange * 100).toFixed(0)}
                            </span>
                          ) : (
                            <span className="text-[9px] text-slate-600">-</span>
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
