export const dynamic = "force-dynamic";

import { rca } from "@/lib/supabase";

export default async function MemoryPage({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  const { data: memories } = await rca
    .from("memory")
    .select("dt,memory_type,topic,content,created_at,signal_label")
    .eq("city_id", cityId)
    .order("created_at", { ascending: false })
    .limit(30);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">Memory</h2>
        <p className="mt-1 text-sm text-slate-400">Short lessons distilled automatically after each RCA run.</p>
      </div>

      {(!memories || memories.length === 0) && (
        <div className="glass-card rounded-2xl p-8 text-center text-slate-400">
          No memory items yet. Run `rca run --city {cityId} --date YYYY-MM-DD` to create the first lesson.
        </div>
      )}

      <div className="space-y-4">
        {memories?.map((memory, index) => (
          <div key={`${memory.created_at}-${index}`} className="glass-card rounded-2xl p-6">
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span>{memory.dt}</span>
              <span>{memory.memory_type}</span>
              <span>{memory.topic}</span>
              <span>{memory.signal_label}</span>
              <span className="ml-auto">{new Date(memory.created_at).toLocaleString()}</span>
            </div>
            <pre className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{memory.content}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
