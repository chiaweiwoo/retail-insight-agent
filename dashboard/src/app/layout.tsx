import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

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
      <body className={`${inter.className} bg-slate-950 text-slate-50 min-h-screen antialiased flex flex-col`}>
        <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-slate-950/80 backdrop-blur-md">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]">
                RI
              </div>
              <span className="text-xl font-semibold tracking-tight text-slate-100">Retail Insight RCA</span>
            </Link>
            <nav className="flex space-x-6 text-sm font-medium text-slate-300">
              <Link href="/" className="hover:text-white transition-colors">Stores</Link>
              <Link href="#" className="hover:text-white transition-colors">Signals</Link>
              <Link href="#" className="hover:text-white transition-colors">Settings</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 container mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
