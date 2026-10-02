import { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Trash2, Loader2 } from 'lucide-react';
import { api } from '../api';

export function RootLayout() {
  const navigate = useNavigate();
  const [isClearing, setIsClearing] = useState(false);

  const handleClearCache = async () => {
    if (!window.confirm("Are you sure you want to delete all processed images and clear the queue?")) return;
    
    setIsClearing(true);
    try {
      await api.clearCache();
      navigate('/');
    } catch (e) {
      alert("Failed to clear cache");
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="min-h-screen bg-base text-foreground flex flex-col">
      <header className="border-b border-panel-light bg-panel/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4 cursor-pointer" onClick={() => navigate('/')}>
            <img src="/ogma_logo.jpg" alt="Ogma Logo" className="h-10 w-10 object-contain rounded-md" />
            <h1 className="text-xl font-bold tracking-tight text-primary">Ogma</h1>
          </div>
          <button
            onClick={handleClearCache}
            disabled={isClearing}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-md transition-colors disabled:opacity-50"
          >
            {isClearing ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            Clear Cache
          </button>
        </div>
      </header>
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
