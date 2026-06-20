export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import { Card, Title, Text, Metric, Grid } from "@tremor/react";

export default async function ProfilePage({ params }: { params: Promise<{ storeId: string }> }) {
  const { storeId } = await params;
  const { data: profile, error } = await supabase
    .from("rca_store_profile")
    .select("*")
    .eq("store_id", storeId)
    .single();

  if (error) {
    // If no profile exists, it might throw a single row error, we handle it gracefully
    return (
      <div className="space-y-6">
        <Title className="text-slate-50">Store Profile & Memory</Title>
        <Text className="text-slate-400">No distilled profile memory exists for this store yet.</Text>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Title className="text-slate-50">Store Profile & Memory</Title>
      
      <Grid numItemsSm={1} numItemsMd={3} className="gap-6">
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Total Triggers</Text>
          <Metric className="text-slate-50">{profile.trigger_count || 0}</Metric>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Drop Count</Text>
          <Metric className="text-red-400">{profile.drop_count || 0}</Metric>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Lift Count</Text>
          <Metric className="text-emerald-400">{profile.lift_count || 0}</Metric>
        </Card>
      </Grid>

      <Card className="bg-slate-900/50 border-slate-800 p-6">
        <Title className="text-slate-50 mb-4">Memory Narrative</Title>
        <Text className="text-slate-300 whitespace-pre-wrap leading-relaxed">
          {profile.narrative || "No narrative generated yet."}
        </Text>
      </Card>

      <Grid numItemsSm={1} numItemsMd={2} className="gap-6">
        <Card className="bg-slate-900/50 border-slate-800 p-6">
          <Title className="text-slate-50 mb-4">Common Drivers</Title>
          <pre className="text-slate-300 text-sm whitespace-pre-wrap font-sans">
            {JSON.stringify(profile.common_drivers, null, 2)}
          </pre>
        </Card>
        
        <Card className="bg-slate-900/50 border-slate-800 p-6">
          <Title className="text-slate-50 mb-4">Recurring Notes</Title>
          <pre className="text-slate-300 text-sm whitespace-pre-wrap font-sans">
            {JSON.stringify(profile.recurring_notes, null, 2)}
          </pre>
        </Card>
      </Grid>
      
      <Text className="text-slate-500 text-sm mt-4">
        Profile last updated: {new Date(profile.updated_at).toLocaleString()}
      </Text>
    </div>
  );
}
