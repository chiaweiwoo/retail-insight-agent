import Link from "next/link";
import { Flex, Title } from "@tremor/react";

export default async function StoreLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ storeId: string }>;
}) {
  const { storeId } = await params;
  return (
    <div className="space-y-6">
      <Flex alignItems="baseline" className="border-b border-slate-800 pb-4">
        <Title className="text-3xl text-slate-50 font-bold tracking-tight">Store {storeId}</Title>
        <nav className="flex space-x-6">
          <Link href={`/stores/${storeId}`} className="text-slate-400 hover:text-slate-50 transition-colors text-sm font-medium">Overview</Link>
          <Link href={`/stores/${storeId}/rca`} className="text-slate-400 hover:text-slate-50 transition-colors text-sm font-medium">Decision Cards</Link>
          <Link href={`/stores/${storeId}/profile`} className="text-slate-400 hover:text-slate-50 transition-colors text-sm font-medium">Profile & Memory</Link>
        </nav>
      </Flex>
      {children}
    </div>
  );
}
