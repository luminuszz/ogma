import React from 'react';
import { Outlet } from 'react-router-dom';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-base text-foreground flex flex-col">
      <header className="border-b border-panel-light bg-panel/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-4">
          <img src="/ogma_logo.jpg" alt="Ogma Logo" className="h-10 w-10 object-contain rounded-md" />
          <h1 className="text-xl font-bold tracking-tight text-primary">Ogma</h1>
        </div>
      </header>
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
