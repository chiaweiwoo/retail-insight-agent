export const dynamic = "force-dynamic";

import { rca } from "@/lib/supabase";

export default async function LogsPage({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  const [{ data: events }, { data: completions }] = await Promise.all([
    rca.from("events").select("run_id,dt,seq,actor_type,actor_name,action,source,details").eq("city_id", cityId).order("id", { ascending: false }).limit(120),
    rca.from("completions").select("run_id,dt,node_name,model,prompt_tokens,completion_tokens,content").eq("city_id", cityId).order("id", { ascending: false }).limit(40),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">Workflow Logs</h2>
        <p className="mt-1 text-sm text-slate-400">Planner decisions, tool calls, completions, and memory-related traces for this city.</p>
      </div>

      <section className="glass-card rounded-2xl p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Recent Events</h3>
        <div className="space-y-3">
          {(events || []).map((event) => (
            <div key={`${event.run_id}-${event.seq}`} className="rounded-xl border border-white/5 bg-[#111114] p-4">
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <span>{event.dt}</span>
                <span>{event.actor_type}</span>
                <span>{event.actor_name}</span>
                <span>{event.action}</span>
                <span className="font-mono">{event.run_id}</span>
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-sm text-slate-300">{JSON.stringify(event.details, null, 2)}</pre>
            </div>
          ))}
        </div>
      </section>

      <section className="glass-card rounded-2xl p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Recent LLM Completions</h3>
        <div className="space-y-4">
          {(completions || []).map((completion, index) => (
            <details key={`${completion.run_id}-${completion.node_name}-${index}`} className="rounded-xl border border-white/5 bg-[#111114] p-4">
              <summary className="cursor-pointer list-none text-sm font-medium text-slate-200">
                {completion.node_name} on {completion.dt} <span className="text-slate-500">({completion.model})</span>
              </summary>
              <div className="mt-3 text-xs text-slate-500">
                prompt tokens: {completion.prompt_tokens ?? "?"} | completion tokens: {completion.completion_tokens ?? "?"}
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-sm text-slate-300">{completion.content}</pre>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
