export const dynamic = "force-dynamic";

import { CheckCircle2, Clock, FileText, MessageSquareWarning } from "lucide-react";
import { rca } from "@/lib/supabase";

export default async function RCAPage({
  params,
  searchParams,
}: {
  params: Promise<{ cityId: string }>;
  searchParams: Promise<{ date?: string }>;
}) {
  const { cityId } = await params;
  const cityKey = Number(cityId);
  const { date } = await searchParams;
  const { data: outcomes, error } = await rca
    .from("outcomes")
    .select("city_id,dt,signal_label,confidence,headline,decision_card_markdown,report_markdown,prediction_markdown,prescription_markdown,generated_at")
    .eq("city_id", cityKey)
    .order("dt", { ascending: false });

  if (error) {
    return <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-300">{error.message}</div>;
  }

  const ordered = date
    ? [...(outcomes || [])].sort((left, right) => (left.dt === date ? -1 : right.dt === date ? 1 : right.dt.localeCompare(left.dt)))
    : outcomes || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">RCA Results</h2>
        <p className="mt-1 text-sm text-slate-400">Clicking a signal marker sends you here. The most recently selected city/date appears first.</p>
      </div>

      {ordered.length === 0 && (
        <div className="glass-card rounded-2xl p-8 text-center text-slate-400">
          No RCA results found for this city yet. Run `rca run --city {cityId} --date YYYY-MM-DD` to generate one.
        </div>
      )}

      <div className="space-y-6">
        {ordered.map((outcome) => (
          <div key={outcome.dt} className={`glass-card overflow-hidden rounded-2xl ${date === outcome.dt ? "ring-1 ring-teal-400/50" : ""}`}>
            <div className="border-b border-white/5 bg-white/[0.02] p-6">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 py-1.5">
                  <Clock size={14} className="text-slate-400" />
                  <span className="font-mono text-sm text-slate-300">{outcome.dt}</span>
                </div>
                {outcome.confidence === "high" ? (
                  <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1.5 text-xs font-medium text-emerald-400">
                    <CheckCircle2 size={14} />
                    <span>High Confidence</span>
                  </div>
                ) : outcome.confidence === "low" ? (
                  <div className="flex items-center gap-1.5 rounded-lg border border-amber-500/20 bg-amber-500/10 px-2.5 py-1.5 text-xs font-medium text-amber-400">
                    <MessageSquareWarning size={14} />
                    <span>Low Confidence</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 rounded-lg border border-sky-500/20 bg-sky-500/10 px-2.5 py-1.5 text-xs font-medium text-sky-400">
                    <CheckCircle2 size={14} />
                    <span className="capitalize">{outcome.confidence} Confidence</span>
                  </div>
                )}
                <div className="rounded-lg border border-white/10 bg-slate-900 px-2.5 py-1.5 text-xs font-medium uppercase tracking-wider text-slate-300">
                  {outcome.signal_label}
                </div>
                {outcome.generated_at && <div className="ml-auto text-xs font-mono text-slate-500">analysed {new Date(outcome.generated_at).toLocaleString()}</div>}
              </div>
              <h3 className="text-xl font-semibold text-white">{outcome.headline}</h3>
            </div>

            <div className="space-y-5 p-6">
              <section>
                <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
                  <FileText size={14} />
                  <span>Decision Card</span>
                </div>
                <pre className="rounded-xl border border-white/5 bg-[#111114] p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{outcome.decision_card_markdown}</pre>
              </section>

              <section className="grid gap-5 xl:grid-cols-2">
                <div>
                  <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">RCA</div>
                  <pre className="rounded-xl border border-white/5 bg-[#111114] p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{outcome.report_markdown}</pre>
                </div>
                <div className="space-y-5">
                  <div>
                    <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Prediction</div>
                    <pre className="rounded-xl border border-white/5 bg-[#111114] p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{outcome.prediction_markdown}</pre>
                  </div>
                  <div>
                    <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Prescription</div>
                    <pre className="rounded-xl border border-white/5 bg-[#111114] p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{outcome.prescription_markdown}</pre>
                  </div>
                </div>
              </section>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
