'use client';

import React from 'react';
import TickerHeader from '@/components/TickerHeader';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col overflow-hidden">
      {/* Consistent Top Header */}
      <TickerHeader />
      
      <main className="flex-1 overflow-y-auto overflow-x-hidden p-6">
        {children}
      </main>
    </div>
  );
}
