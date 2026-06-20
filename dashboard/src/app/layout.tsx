import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { Activity, BarChart2, Store } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Retail Insight RCA",
  description: "AI-Powered Root Cause Analysis for Retail Signals",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0A0A0B] text-slate-50 min-h-screen antialiased flex selection:bg-indigo-500/30`}>
        {/* Sidebar */}
        <aside className="w-64 border-r border-white/5 bg-[#0F0F12] hidden md:flex flex-col sticky top-0 h-screen">
          <div className="p-6">
            <Link href="/" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-[0_0_20px_rgba(99,102,241,0.3)] group-hover:shadow-[0_0_25px_rgba(99,102,241,0.5)] transition-all">
                <Activity size={20} />
              </div>
              <div>
                <h1 className="font-semibold tracking-tight text-slate-100 text-lg leading-tight group-hover:text-white transition-colors">Retail Insight</h1>
                <p className="text-xs text-slate-500 font-medium tracking-wider">AGENTIC RCA</p>
              </div>
            </Link>
          </div>
          
          <nav className="flex-1 px-4 space-y-1 mt-4">
            <Link href="/" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg bg-indigo-500/10 text-indigo-400 font-medium transition-colors">
              <Store size={18} />
              <span>Fleet Overview</span>
            </Link>
            <Link href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-white/5 hover:text-slate-200 font-medium transition-colors">
              <BarChart2 size={18} />
              <span>Signals Grid</span>
            </Link>
          </nav>
          
          <div className="p-4 mt-auto">
            <div className="p-4 rounded-xl bg-gradient-to-b from-white/5 to-transparent border border-white/5">
              <p className="text-xs text-slate-400 mb-3">Supabase RLS Active</p>
              <div className="flex items-center space-x-2 text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2.5 py-1.5 rounded-full w-max border border-emerald-400/20">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                <span>Anon Connected</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 flex flex-col">
          {/* Mobile Header */}
          <header className="md:hidden sticky top-0 z-50 w-full border-b border-white/5 bg-[#0A0A0B]/80 backdrop-blur-md px-4 h-16 flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]">
                <Activity size={16} />
              </div>
              <span className="font-semibold tracking-tight text-slate-100">Retail Insight</span>
            </Link>
          </header>
          
          <div className="flex-1 container mx-auto p-4 md:p-8 max-w-7xl">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
