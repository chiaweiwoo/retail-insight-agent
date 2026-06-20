export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import { BrainCircuit, BookOpen, AlertCircle, History, TrendingDown, TrendingUp } from "lucide-react";

export default async function ProfilePage({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  const { data: profile, error } = await supabase
    .from("rca_city_profile")
    .select("*")
    .eq("city_id", cityId)
    .single();

  if (error || !profile) {
    return (
      <div className="space-y-6 animate-in fade-in duration-700">
        <div>
          <h2 className="text-2xl font-semibold text-slate-50">Store Profile & Semantic Memory</h2>
          <p className="text-slate-400 text-sm mt-1">Distilled longitudinal patterns for City {cityId}</p>
        </div>
        <div className="glass-card rounded-2xl p-8 text-center flex flex-col items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
            <BrainCircuit size={24} className="text-slate-500" />
          </div>
          <h3 className="text-lg font-medium text-slate-200">No profile memory exists</h3>
          <p className="text-slate-400 text-sm mt-2 max-w-sm">
            This city has not had its history distilled into a semantic profile yet. Run <code className="text-xs bg-black/50 px-1.5 py-0.5 rounded text-indigo-400">rca distil</code> to generate one.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">Store Profile & Semantic Memory</h2>
        <p className="text-slate-400 text-sm mt-1">Distilled longitudinal patterns for City {cityId}</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <History size={48} />
          </div>
          <p className="text-slate-400 text-sm font-medium mb-2">Total Triggers Analyzed</p>
          <p className="text-4xl font-bold text-white">{profile.trigger_count || 0}</p>
        </div>
        
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group border-rose-500/10">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-rose-500 group-hover:opacity-20 transition-opacity">
            <TrendingDown size={48} />
          </div>
          <p className="text-slate-400 text-sm font-medium mb-2">Drop Count</p>
          <p className="text-4xl font-bold text-rose-400">{profile.drop_count || 0}</p>
        </div>
        
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group border-emerald-500/10">
          <div className="absolute top-0 right-0 p-4 opacity-10 text-emerald-500 group-hover:opacity-20 transition-opacity">
            <TrendingUp size={48} />
          </div>
          <p className="text-slate-400 text-sm font-medium mb-2">Lift Count</p>
          <p className="text-4xl font-bold text-emerald-400">{profile.lift_count || 0}</p>
        </div>
      </div>

      <div className="glass-card rounded-2xl p-1 shadow-[0_0_30px_rgba(99,102,241,0.05)]">
        <div className="bg-[#111114] rounded-[15px] p-6">
          <div className="flex items-center space-x-3 mb-4">
            <BookOpen className="text-indigo-400" size={20} />
            <h3 className="text-lg font-semibold text-white">Memory Narrative</h3>
          </div>
          <p className="text-slate-300 leading-relaxed font-serif text-lg">
            {profile.narrative || "No narrative generated yet."}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <BrainCircuit className="text-purple-400" size={18} />
            <h3 className="text-lg font-medium text-white">Common Drivers</h3>
          </div>
          <div className="bg-black/30 rounded-xl p-4 border border-white/5 h-48 overflow-y-auto">
            <pre className="text-slate-300 text-sm whitespace-pre-wrap font-sans">
              {JSON.stringify(profile.common_drivers, null, 2)}
            </pre>
          </div>
        </div>
        
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <AlertCircle className="text-amber-400" size={18} />
            <h3 className="text-lg font-medium text-white">Recurring Notes</h3>
          </div>
          <div className="bg-black/30 rounded-xl p-4 border border-white/5 h-48 overflow-y-auto">
            <pre className="text-slate-300 text-sm whitespace-pre-wrap font-sans">
              {JSON.stringify(profile.recurring_notes, null, 2)}
            </pre>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end">
        <p className="text-slate-500 text-xs font-mono">
          Last distilled: {new Date(profile.updated_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
