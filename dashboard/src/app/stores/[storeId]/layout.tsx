"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { use, useEffect, useState } from "react";
import { LayoutDashboard, FileText, BrainCircuit } from "lucide-react";

export default function StoreLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ storeId: string }>;
}) {
  const resolvedParams = use(params);
  const storeId = resolvedParams.storeId;
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const tabs = [
    {
      name: "Overview",
      href: `/stores/${storeId}`,
      icon: LayoutDashboard,
      active: pathname === `/stores/${storeId}`,
    },
    {
      name: "Decision Cards",
      href: `/stores/${storeId}/rca`,
      icon: FileText,
      active: pathname === `/stores/${storeId}/rca`,
    },
    {
      name: "Profile & Memory",
      href: `/stores/${storeId}/profile`,
      icon: BrainCircuit,
      active: pathname === `/stores/${storeId}/profile`,
    },
  ];

  if (!mounted) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-white/5 space-y-4 md:space-y-0">
        <h1 className="text-3xl text-white font-semibold tracking-tight">Store <span className="text-indigo-400">{storeId}</span></h1>
        <nav className="flex space-x-1 bg-[#111114] p-1 rounded-xl border border-white/5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Link 
                key={tab.name} 
                href={tab.href} 
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  tab.active 
                    ? "bg-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.3)]" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                <Icon size={16} />
                <span>{tab.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>
      {children}
    </div>
  );
}
