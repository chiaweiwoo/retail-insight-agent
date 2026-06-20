export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import SalesChart from "./SalesChart";
import { ArrowLeft, ChevronRight, Activity, TrendingDown, Target, Zap, Clock } from "lucide-react";

export default async function CityOverview({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  
  const { data: salesData, error } = await supabase
    .from("rca_city_series")
    .select("dt, total_sales")
    .eq("city_id", cityId)
    .order("dt", { ascending: true });

  const { data: signals } = await supabase
    .from("rca_outcome")
    .select("dt, signal_label")
    .eq("city_id", cityId)
    .neq("signal_label", "none");

  if (error || !salesData) {
    return (
      <div className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20 glass-panel">
        <h2 className="text-lg font-semibold">Error loading data</h2>
      </div>
    );
  }

  // Calculate descriptive stats
  const sales = salesData.map(d => d.total_sales);
  const mean = sales.length ? sales.reduce((a, b) => a + b, 0) / sales.length : 0;
  const stddev = sales.length ? Math.sqrt(sales.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / sales.length) : 0;

  // Mark triggered dates in chart data
  const signalMap = new Map(signals?.map(s => [s.dt, s.signal_label]) || []);
  
  const chartData = salesData.map(d => ({
    date: d.dt,
    Sales: d.total_sales,
    Trigger: signalMap.get(d.dt) || null,
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center space-x-3 mb-3 text-slate-400">
            <Target size={18} className="text-indigo-400" />
            <span className="text-sm font-medium">Avg Daily Sales</span>
          </div>
          <div className="text-3xl font-bold text-white">{Math.round(mean).toLocaleString()}</div>
          <div className="mt-2 text-xs text-slate-500">Normalized Coefficient</div>
        </div>
        
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center space-x-3 mb-3 text-slate-400">
            <Activity size={18} className="text-purple-400" />
            <span className="text-sm font-medium">Sales Volatility (σ)</span>
          </div>
          <div className="text-3xl font-bold text-white">{Math.round(stddev).toLocaleString()}</div>
          <div className="mt-2 text-xs text-slate-500">Standard Deviation</div>
        </div>
        
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center space-x-3 mb-3 text-slate-400">
            <Zap size={18} className="text-rose-400" />
            <span className="text-sm font-medium">Triggered Days</span>
          </div>
          <div className="text-3xl font-bold text-white">{signals?.length || 0}</div>
          <div className="mt-2 text-xs text-slate-500">Requiring Agent RCA</div>
        </div>

        <div className="glass-card p-5 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-600/10 border-indigo-500/20">
          <div className="flex items-center space-x-3 mb-3 text-indigo-300">
            <Clock size={18} />
            <span className="text-sm font-medium">Next Evaluation</span>
          </div>
          <div className="text-xl font-bold text-indigo-100 mt-2">Active Monitoring</div>
          <div className="mt-2 text-xs text-indigo-300/70">Real-time signal ingestion</div>
        </div>
      </div>

      {/* Main Chart */}
      <div className="glass-card p-6 rounded-2xl relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-32 bg-indigo-500/20 blur-[100px] rounded-full pointer-events-none"></div>
        
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-white">Sales Performance Timeline</h2>
          <div className="flex items-center space-x-4 text-xs font-medium">
            <div className="flex items-center space-x-1.5 text-slate-400">
              <div className="w-2 h-2 rounded-full bg-rose-500"></div>
              <span>RCA Drop Trigger</span>
            </div>
            <div className="flex items-center space-x-1.5 text-slate-400">
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <span>RCA Lift Trigger</span>
            </div>
          </div>
        </div>
        <p className="text-sm text-slate-400 mb-6">Red and green markers indicate dates where LangGraph analysts were dispatched.</p>
        
        <SalesChart data={chartData} />
      </div>
    </div>
  );
}
