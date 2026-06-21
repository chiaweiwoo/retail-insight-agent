"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { use } from "react";
import { BrainCircuit, FileText, History, LayoutDashboard, ScrollText } from "lucide-react";

export default function CityLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ cityId: string }>;
}) {
  const resolvedParams = use(params);
  const cityId = resolvedParams.cityId;
  const pathname = usePathname();

  const tabs = [
    { name: "Overview", href: `/cities/${cityId}`, icon: LayoutDashboard, active: pathname === `/cities/${cityId}` },
    { name: "RCA", href: `/cities/${cityId}/rca`, icon: FileText, active: pathname === `/cities/${cityId}/rca` },
    { name: "Simulation", href: `/cities/${cityId}/simulate`, icon: History, active: pathname === `/cities/${cityId}/simulate` || pathname === `/cities/${cityId}/replay` },
    { name: "Logs", href: `/cities/${cityId}/logs`, icon: ScrollText, active: pathname === `/cities/${cityId}/logs` },
    { name: "Memory", href: `/cities/${cityId}/profile`, icon: BrainCircuit, active: pathname === `/cities/${cityId}/profile` },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 border-b border-white/5 pb-4 md:flex-row md:items-center">
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          City <span className="text-teal-400">{cityId}</span>
        </h1>
        <nav className="flex flex-wrap gap-1 rounded-xl border border-white/5 bg-[#111114] p-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Link
                key={tab.name}
                href={tab.href}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                  tab.active
                    ? "bg-teal-700 text-white shadow-[0_0_18px_rgba(13,148,136,0.28)]"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
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
