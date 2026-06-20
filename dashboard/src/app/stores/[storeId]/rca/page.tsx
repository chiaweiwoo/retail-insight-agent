export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import { Card, Title, Text, Badge, Flex, Grid } from "@tremor/react";

export default async function RCAPage({ params }: { params: Promise<{ storeId: string }> }) {
  const { storeId } = await params;
  const { data: outcomes, error } = await supabase
    .from("rca_outcome")
    .select("*")
    .eq("store_id", storeId)
    .order("dt", { ascending: false });

  if (error) {
    return <div>Error loading RCA outcomes</div>;
  }

  return (
    <div className="space-y-6">
      <Title className="text-slate-50">Decision Cards</Title>
      
      {outcomes?.length === 0 && (
        <Text className="text-slate-400">No RCA outcomes found for this store.</Text>
      )}

      <Grid numItemsSm={1} className="gap-6">
        {outcomes?.map((outcome) => (
          <Card key={`${outcome.run_name}-${outcome.dt}`} className="bg-slate-900/50 border-slate-800 p-6">
            <Flex alignItems="start" className="mb-4">
              <div>
                <Flex className="space-x-3 mb-2" justifyContent="start">
                  <Text className="text-slate-400 font-mono text-sm">{outcome.dt}</Text>
                  {outcome.escalated && (
                    <Badge color="red" className="bg-red-500/10 text-red-400 border border-red-500/20">Escalated</Badge>
                  )}
                  {outcome.confidence === 'high' ? (
                    <Badge color="emerald" className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">High Confidence</Badge>
                  ) : outcome.confidence === 'low' ? (
                    <Badge color="amber" className="bg-amber-500/10 text-amber-400 border border-amber-500/20">Low Confidence</Badge>
                  ) : (
                    <Badge color="blue" className="bg-blue-500/10 text-blue-400 border border-blue-500/20">{outcome.confidence}</Badge>
                  )}
                  <Badge color="slate" className="bg-slate-800 text-slate-300 border border-slate-700">{outcome.signal_label}</Badge>
                </Flex>
                <Title className="text-slate-50 text-xl">{outcome.brief_headline}</Title>
              </div>
            </Flex>
            
            <div className="mt-4 pt-4 border-t border-slate-800">
              <Text className="text-slate-300 font-medium mb-2">Top Driver</Text>
              <Text className="text-slate-400">{outcome.top_driver}</Text>
            </div>

            <div className="mt-4 p-4 bg-slate-950/50 rounded-lg border border-slate-800/50">
              {/* Note: In a real app, we'd use react-markdown here to render outcome.decision_card_md */}
              <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans">
                {outcome.decision_card_md}
              </pre>
            </div>
          </Card>
        ))}
      </Grid>
    </div>
  );
}
