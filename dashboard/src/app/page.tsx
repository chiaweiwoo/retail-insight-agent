export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { Badge, Card, Title, Text, Metric, Flex, Grid, Select, SelectItem } from "@tremor/react";

// Server Component
export default async function StoresPage() {
  // Fetch stores and their latest signal
  const { data: stores, error } = await supabase
    .from("dim_store")
    .select(`
      store_id,
      city_id,
      signals (
        dt,
        signal_label,
        value
      )
    `)
    // Using a simple fetch, assuming there's at least some signals.
    // In a real app, we'd limit this or use a view to get latest.
    .limit(100);

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 text-red-400 rounded-lg border border-red-900/50">
        <h2 className="text-lg font-bold">Error loading stores</h2>
        <p>{error.message}</p>
      </div>
    );
  }

  // Process data to get the latest signal per store
  const processedStores = stores?.map((store: any) => {
    // Sort signals by date descending to get the latest
    const sortedSignals = store.signals?.sort((a: any, b: any) => 
      new Date(b.dt).getTime() - new Date(a.dt).getTime()
    ) || [];
    const latestSignal = sortedSignals[0];

    return {
      store_id: store.store_id,
      city_id: store.city_id,
      latest_dt: latestSignal?.dt || "N/A",
      signal_label: latestSignal?.signal_label || "none",
      value: latestSignal?.value || 0,
    };
  }) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Title className="text-3xl text-slate-50 font-bold tracking-tight">Retail Stores</Title>
          <Text className="text-slate-400 mt-1">Monitor sales signals across the fleet</Text>
        </div>
      </div>

      <Grid numItemsSm={1} numItemsMd={2} numItemsLg={3} className="gap-6">
        {processedStores.map((store) => (
          <Link key={store.store_id} href={`/stores/${store.store_id}`}>
            <Card className="bg-slate-900/50 border-slate-800 hover:bg-slate-800/50 transition-all cursor-pointer group rounded-xl shadow-lg hover:shadow-indigo-500/10">
              <Flex alignItems="start">
                <div>
                  <Text className="text-slate-400 font-medium">Store</Text>
                  <Metric className="text-slate-50 group-hover:text-indigo-400 transition-colors">{store.store_id}</Metric>
                  <Text className="text-slate-500 text-sm mt-1">City {store.city_id}</Text>
                </div>
                {store.signal_label === "drop" ? (
                  <Badge color="red" className="bg-red-500/10 text-red-400 border border-red-500/20">Drop</Badge>
                ) : store.signal_label === "lift" ? (
                  <Badge color="emerald" className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Lift</Badge>
                ) : (
                  <Badge color="slate" className="bg-slate-800 text-slate-400 border border-slate-700">Normal</Badge>
                )}
              </Flex>
              <div className="mt-4 pt-4 border-t border-slate-800/50">
                <Flex>
                  <Text className="text-slate-500">Last Signal: {store.latest_dt}</Text>
                  <Text className={`font-medium ${store.value < 0 ? 'text-red-400' : store.value > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {store.value > 0 ? '+' : ''}{(store.value * 100).toFixed(1)}%
                  </Text>
                </Flex>
              </div>
            </Card>
          </Link>
        ))}
      </Grid>
    </div>
  );
}
