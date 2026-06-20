export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import { AlertCircle, Clock, FileText, CheckCircle2, AlertTriangle, MessageSquareWarning } from "lucide-react";

export default async function RCAPage({ params }: { params: Promise<{ storeId: string }> }) {
  const { storeId } = await params;
  const { data: outcomes, error } = await supabase
    .from("rca_outcome")
    .select("*")
    .eq("store_id", storeId)
    .order("dt", { ascending: false });

  if (error) {
    return (
      <div className="p-4 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20 glass-panel">
        <h2 className="text-lg font-semibold flex items-center space-x-2">
          <AlertTriangle size={20} />
          <span>Error loading RCA outcomes</span>
        </h2>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">Decision Cards</h2>
        <p className="text-slate-400 text-sm mt-1">Historical RCA reports for Store {storeId}</p>
      </div>
      
      {(!outcomes || outcomes.length === 0) && (
        <div className="glass-card rounded-2xl p-8 text-center flex flex-col items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
            <FileText size={24} className="text-slate-500" />
          </div>
          <h3 className="text-lg font-medium text-slate-200">No RCA outcomes found</h3>
          <p className="text-slate-400 text-sm mt-2 max-w-sm">
            This store has not triggered any automated root cause analysis investigations yet.
          </p>
        </div>
      )}

      <div className="space-y-6">
        {outcomes?.map((outcome) => (
          <div key={`${outcome.run_name}-${outcome.dt}`} className="glass-card rounded-2xl overflow-hidden group">
            {/* Header */}
            <div className="p-6 border-b border-white/5 bg-white/[0.01]">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <div className="flex items-center space-x-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
                  <Clock size={14} className="text-slate-400" />
                  <span className="text-slate-300 font-mono text-sm">{outcome.dt}</span>
                </div>
                
                {outcome.escalated && (
                  <div className="flex items-center space-x-1.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2.5 py-1.5 rounded-lg text-xs font-medium shadow-[0_0_10px_rgba(244,63,94,0.1)]">
                    <AlertCircle size={14} />
                    <span>Escalated</span>
                  </div>
                )}
                
                {outcome.confidence === 'high' ? (
                  <div className="flex items-center space-x-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-1.5 rounded-lg text-xs font-medium">
                    <CheckCircle2 size={14} />
                    <span>High Confidence</span>
                  </div>
                ) : outcome.confidence === 'low' ? (
                  <div className="flex items-center space-x-1.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-1.5 rounded-lg text-xs font-medium">
                    <MessageSquareWarning size={14} />
                    <span>Low Confidence</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-1.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-1.5 rounded-lg text-xs font-medium">
                    <CheckCircle2 size={14} />
                    <span className="capitalize">{outcome.confidence} Confidence</span>
                  </div>
                )}
                
                <div className="bg-slate-800 border border-slate-700 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 uppercase tracking-wider">
                  {outcome.signal_label}
                </div>
              </div>
              
              <h3 className="text-xl font-semibold text-white leading-tight">{outcome.brief_headline}</h3>
              
              <div className="mt-4 pt-4 border-t border-white/5">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Primary Driver</span>
                <p className="text-slate-300 font-medium mt-1">{outcome.top_driver}</p>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 bg-[#0A0A0B]/30">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3 block">SLT Brief / Decision Card</span>
              <div className="bg-[#111114] rounded-xl border border-white/5 p-5 shadow-inner">
                <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans leading-relaxed">
                  {outcome.decision_card_md}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
