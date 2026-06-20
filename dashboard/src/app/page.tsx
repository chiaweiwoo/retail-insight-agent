export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { AlertTriangle, TrendingUp, TrendingDown, Store, ArrowRight, Activity } from "lucide-react";

export default async function StoresPage() {
  const { data: stores, error: storesError } = await supabase
    .from("rca_city_normals")
    .select("city_id, density_tier")
    .limit(100);

  if (storesError) {
    return (
      <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20 glass-panel">
        <h2 className="text-lg font-semibold flex items-center space-x-2">
          <AlertTriangle size={20} />
          <span>Database Connection Error</span>
        </h2>
        <p className="mt-2 opacity-80">{storesError.message}</p>
      </div>
    );
  }

  // Fetch recent signals to get latest signal per store and for the heatmap
  const { data: outcomes } = await supabase
    .from("rca_outcome")
    .select("city_id, dt, signal_label, escalated")
    .order("dt", { ascending: false });

  // Get unique dates for heatmap (last 14 days with signals)
  const allDates = Array.from(new Set((outcomes || []).map(o => o.dt))).sort((a, b) => b.localeCompare(a)).slice(0, 14).reverse();

  // Process data per store
  const processedStores = stores?.map((store: any) => {
    const storeOutcomes = outcomes?.filter(o => o.city_id === store.city_id) || [];
    const latestSignal = storeOutcomes[0];
    
    // Build heatmap data for this store
    const heatmapCells = allDates.map(date => {
      const daySignal = storeOutcomes.find(o => o.dt === date);
      return {
        date,
        signal: daySignal?.signal_label || "none",
        escalated: daySignal?.escalated || false
      };
    });

    return {
      city_id: store.city_id,
      density_tier: store.density_tier,
      latest_dt: latestSignal?.dt || "N/A",
      signal_label: latestSignal?.signal_label || "none",
      heatmapCells,
      total_anomalies: storeOutcomes.length
    };
  }) || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Fleet Overview</h1>
          <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed">
            Monitor sales signals across the fleet. The agentic RCA system automatically detects drops and lifts, dispatching parallel specialists to investigate root causes before synthesizing a final executive brief.
          </p>
        </div>
        <div className="hidden md:flex items-center space-x-4 bg-indigo-500/10 border border-indigo-500/20 px-4 py-2 rounded-full">
          <div className="flex items-center space-x-2 text-indigo-400">
            <Activity size={16} className="animate-pulse" />
            <span className="text-sm font-medium tracking-wide">System Online</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {processedStores.map((store) => (
          <Link key={store.city_id} href={`/cities/${store.city_id}`} className="group outline-none">
            <div className="glass-card rounded-2xl p-6 transition-all duration-300 hover:scale-[1.02] hover:bg-white/[0.03] hover:border-indigo-500/30 group-focus:ring-2 ring-indigo-500 ring-offset-2 ring-offset-[#0A0A0B]">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-slate-800/50 border border-white/10 flex items-center justify-center text-slate-300 group-hover:text-indigo-400 group-hover:border-indigo-500/30 transition-colors">
                    <Store size={18} />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-slate-200 group-hover:text-white transition-colors">City {store.city_id}</h3>
                    <p className="text-xs text-slate-500 font-medium capitalize">{store.density_tier?.trim() || "City Aggregate"}</p>
                  </div>
                </div>
                
                {store.signal_label === "drop" ? (
                  <div className="flex items-center space-x-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2.5 py-1 rounded-full text-xs font-medium shadow-[0_0_10px_rgba(244,63,94,0.1)]">
                    <TrendingDown size={14} />
                    <span>Drop Detected</span>
                  </div>
                ) : store.signal_label === "lift" ? (
                  <div className="flex items-center space-x-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-full text-xs font-medium shadow-[0_0_10px_rgba(16,185,129,0.1)]">
                    <TrendingUp size={14} />
                    <span>Lift Detected</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-1.5 bg-slate-800/50 text-slate-400 border border-slate-700/50 px-2.5 py-1 rounded-full text-xs font-medium">
                    <span>Stable</span>
                  </div>
                )}
              </div>

              {/* Signal Heatmap (14 days) */}
              <div className="mt-6 pt-5 border-t border-white/5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-slate-500 font-medium">14-Day Signal History</span>
                  <span className="text-xs text-slate-600 font-medium">{store.total_anomalies} Total</span>
                </div>
                <div className="flex space-x-1">
                  {store.heatmapCells.map((cell, i) => (
                    <div 
                      key={i} 
                      title={`${cell.date}: ${cell.signal}`}
                      className={`h-6 rounded-[3px] flex-1 transition-colors ${
                        cell.signal === "drop" ? "bg-rose-500/40 hover:bg-rose-500/60" :
                        cell.signal === "lift" ? "bg-emerald-500/40 hover:bg-emerald-500/60" :
                        "bg-white/5 hover:bg-white/10"
                      }`}
                    />
                  ))}
                </div>
              </div>
              
              <div className="mt-5 flex items-center justify-between text-xs font-medium text-slate-500 group-hover:text-indigo-400 transition-colors">
                <span>Last updated: {store.latest_dt}</span>
                <ArrowRight size={14} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
