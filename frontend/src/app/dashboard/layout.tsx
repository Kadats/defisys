'use client';

import React from 'react';
import Sidebar from '@/components/Sidebar';
import TickerHeader from '@/components/TickerHeader';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-slate-950 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TickerHeader />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 bg-grid">
          <div className="animate-fade-in-up">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
