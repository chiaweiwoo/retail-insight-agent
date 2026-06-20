export const dynamic = "force-dynamic";
import { supabase } from "@/lib/supabase";
import { Card, Title, AreaChart, Grid, Metric, Text, Flex } from "@tremor/react";

export default async function StoreOverview({ params }: { params: Promise<{ storeId: string }> }) {
  const { storeId } = await params;
  const { data: salesData, error } = await supabase
    .from("rca_store_series")
    .select("dt, total_sales")
    .eq("store_id", storeId)
    .order("dt", { ascending: true });

  const { data: signals } = await supabase
    .from("rca_outcome")
    .select("dt, signal_label")
    .eq("store_id", storeId)
    .neq("signal_label", "none");

  if (error || !salesData) {
    return <div>Error loading data</div>;
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
    <div className="space-y-6">
      <Grid numItemsSm={1} numItemsLg={3} className="gap-6">
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Average Daily Sales</Text>
          <Metric className="text-slate-50">{mean.toFixed(2)}</Metric>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Sales StdDev</Text>
          <Metric className="text-slate-50">{stddev.toFixed(2)}</Metric>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <Text className="text-slate-400">Triggered Days</Text>
          <Metric className="text-slate-50">{signals?.length || 0}</Metric>
        </Card>
      </Grid>

      <Card className="bg-slate-900/50 border-slate-800 p-6">
        <Title className="text-slate-50 mb-4">Sales Performance</Title>
        <AreaChart
          className="h-80 mt-4"
          data={chartData}
          index="date"
          categories={["Sales"]}
          colors={["indigo"]}
          yAxisWidth={60}
          showAnimation={true}
        />
      </Card>
    </div>
  );
}
