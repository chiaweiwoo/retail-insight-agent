export const dynamic = "force-dynamic";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, History, Link2, RotateCcw, ShieldCheck } from "lucide-react";
import { rca } from "@/lib/supabase";

type ReplayReviewRow = {
  batch_id: string;
  run_id: string;
  city_id: number;
  dt: string;
  signal_label: string;
  eval_score: number;
  eval_passed: boolean;
  alignment_score: number | null;
  alignment_label: string | null;
  pros: string[] | null;
  cons: string[] | null;
  improvements: string[] | null;
  reviewer_comment: string;
  deterministic_checks: { name: string; passed: boolean; severity: string; message: string }[] | null;
  created_at: string;
};

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function scoreTone(score: number | null): string {
  if (score === null) return "text-slate-400";
  if (score >= 0.75) return "text-emerald-400";
  if (score >= 0.5) return "text-amber-400";
  return "text-rose-400";
}

export default async function ReplayPage({ params }: { params: Promise<{ cityId: string }> }) {
  const { cityId } = await params;
  const cityKey = Number(cityId);
  const { data, error } = await rca
    .from("replay_review")
    .select(
      "batch_id,run_id,city_id,dt,signal_label,eval_score,eval_passed,alignment_score,alignment_label,pros,cons,improvements,reviewer_comment,deterministic_checks,created_at",
    )
    .eq("city_id", cityKey)
    .order("created_at", { ascending: false })
    .limit(120);

  if (error) {
    return <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-300">{error.message}</div>;
  }

  const reviews = (data || []) as ReplayReviewRow[];
  const grouped = new Map<string, ReplayReviewRow[]>();
  for (const row of reviews) {
    const existing = grouped.get(row.batch_id) || [];
    existing.push(row);
    grouped.set(row.batch_id, existing);
  }

  const batches = Array.from(grouped.entries()).map(([batchId, rows]) => {
    const evalScores = rows.map((row) => Number(row.eval_score || 0));
    const alignScores = rows.flatMap((row) => (row.alignment_score === null ? [] : [Number(row.alignment_score)]));
    const passCount = rows.filter((row) => row.eval_passed).length;
    return {
      batchId,
      rows: [...rows].sort((left, right) => left.dt.localeCompare(right.dt)),
      avgEval: average(evalScores),
      avgAlign: average(alignScores),
      passCount,
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-50">Replay Review</h2>
        <p className="mt-1 text-sm text-slate-400">
          Batch-level learning view for <code>rca replay --city {cityId}</code>. Each batch shows the per-date evaluator score, alignment
          review, and recurring weaknesses.
        </p>
      </div>

      {batches.length === 0 && (
        <div className="glass-card rounded-2xl p-8 text-center text-slate-400">
          No replay reviews yet. Run <code>rca replay --city {cityId}</code> to create the first batch, or use <code>--reset</code> for a
          cold-start replay.
        </div>
      )}

      {batches.map((batch) => (
        <section key={batch.batchId} className="glass-card overflow-hidden rounded-2xl">
          <div className="border-b border-white/5 bg-white/[0.02] p-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                  <History size={14} />
                  <span>Replay Batch</span>
                </div>
                <h3 className="font-mono text-lg text-white">{batch.batchId}</h3>
                <p className="max-w-3xl text-sm leading-relaxed text-slate-400">
                  Full-city simulation for City {cityId}. Dates run oldest to latest so memory can accumulate and later runs can be compared
                  against earlier ones.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/5 bg-[#111114] px-4 py-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Dates</div>
                  <div className="mt-1 text-xl font-semibold text-white">{batch.rows.length}</div>
                </div>
                <div className="rounded-xl border border-white/5 bg-[#111114] px-4 py-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Avg Eval</div>
                  <div className={`mt-1 text-xl font-semibold ${scoreTone(batch.avgEval)}`}>{batch.avgEval?.toFixed(2) ?? "n/a"}</div>
                </div>
                <div className="rounded-xl border border-white/5 bg-[#111114] px-4 py-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Avg Align</div>
                  <div className={`mt-1 text-xl font-semibold ${scoreTone(batch.avgAlign)}`}>{batch.avgAlign?.toFixed(2) ?? "n/a"}</div>
                  <div className="mt-1 text-xs text-slate-500">{batch.passCount} passed deterministic eval</div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4 p-6">
            {batch.rows.map((row) => {
              const failedChecks = (row.deterministic_checks || []).filter((check) => !check.passed);
              return (
                <details key={`${row.batch_id}-${row.run_id}`} className="rounded-2xl border border-white/5 bg-[#111114] p-5">
                  <summary className="cursor-pointer list-none">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wider text-slate-500">
                          <span>{row.dt}</span>
                          <span>{row.signal_label}</span>
                          <span className="font-mono normal-case tracking-normal">{row.run_id}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
                          <span className={`font-semibold ${scoreTone(Number(row.eval_score))}`}>Eval {Number(row.eval_score).toFixed(2)}</span>
                          <span className={`font-semibold ${scoreTone(row.alignment_score)}`}>
                            Align {row.alignment_score === null ? "n/a" : Number(row.alignment_score).toFixed(2)}
                          </span>
                          <span className="rounded-lg border border-white/10 px-2 py-1 text-xs text-slate-300">
                            {row.alignment_label || "unlabeled"}
                          </span>
                          {row.eval_passed ? (
                            <span className="inline-flex items-center gap-1 text-emerald-400">
                              <CheckCircle2 size={14} />
                              Passed
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-rose-400">
                              <AlertTriangle size={14} />
                              Failed
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={`/cities/${cityId}/rca?date=${row.dt}`}
                          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 hover:bg-white/10"
                        >
                          <Link2 size={14} />
                          Open RCA
                        </Link>
                      </div>
                    </div>
                  </summary>

                  <div className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_1fr]">
                    <div className="space-y-5">
                      <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                        <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
                          <ShieldCheck size={14} />
                          <span>Reviewer Comment</span>
                        </div>
                        <p className="text-sm leading-relaxed text-slate-300">{row.reviewer_comment || "No reviewer comment stored."}</p>
                      </div>

                      <div className="grid gap-4 md:grid-cols-3">
                        <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Pros</div>
                          <ul className="space-y-2 text-sm leading-relaxed text-slate-300">
                            {(row.pros || []).length === 0 && <li className="text-slate-500">No positive notes stored.</li>}
                            {(row.pros || []).map((item, index) => (
                              <li key={index}>- {item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">Cons</div>
                          <ul className="space-y-2 text-sm leading-relaxed text-slate-300">
                            {(row.cons || []).length === 0 && <li className="text-slate-500">No recurring weakness stored.</li>}
                            {(row.cons || []).map((item, index) => (
                              <li key={index}>- {item}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
                            <RotateCcw size={14} />
                            <span>Improvements</span>
                          </div>
                          <ul className="space-y-2 text-sm leading-relaxed text-slate-300">
                            {(row.improvements || []).length === 0 && <li className="text-slate-500">No improvement suggestion stored.</li>}
                            {(row.improvements || []).map((item, index) => (
                              <li key={index}>- {item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/5 bg-black/20 p-4">
                      <div className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-500">Deterministic Checks</div>
                      <div className="space-y-3">
                        {(row.deterministic_checks || []).length === 0 && <p className="text-sm text-slate-500">No check payload stored.</p>}
                        {(row.deterministic_checks || []).map((check, index) => (
                          <div key={`${check.name}-${index}`} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-mono text-xs text-slate-300">{check.name}</span>
                              <span
                                className={`rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
                                  check.passed ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                                }`}
                              >
                                {check.passed ? "pass" : "fail"}
                              </span>
                            </div>
                            <div className="mt-2 text-[11px] uppercase tracking-wider text-slate-500">{check.severity}</div>
                            {!check.passed && check.message && <p className="mt-2 text-sm leading-relaxed text-slate-300">{check.message}</p>}
                          </div>
                        ))}
                      </div>

                      {failedChecks.length > 0 && (
                        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-200">
                          {failedChecks.length} deterministic check{failedChecks.length === 1 ? "" : "s"} failed in this review.
                        </div>
                      )}
                    </div>
                  </div>
                </details>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
