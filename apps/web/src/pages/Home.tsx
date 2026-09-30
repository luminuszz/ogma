import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2 } from 'lucide-react';
import { api } from '../api';

export function Home() {
  const [chapterId, setChapterId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chapterId.trim()) return;

    setError(null);
    setIsLoading(true);

    try {
      // In a real flow, we could just start download and go to reader page, 
      // or redirect and let reader handle polling.
      await api.startDownload(chapterId);
      navigate(`/reader/${encodeURIComponent(chapterId)}`);
    } catch (err: any) {
      setError(err.message || 'Failed to start reading session');
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-panel rounded-2xl shadow-xl overflow-hidden border border-panel-light">
        <div className="p-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-2">Read Manga</h2>
            <p className="text-foreground-muted text-sm">
              Enter a MangaDex Chapter ID or URL to start reading.
            </p>
          </div>

          <form onSubmit={handleStart} className="space-y-4">
            <div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-foreground-muted">
                  <Search size={18} />
                </div>
                <input
                  type="text"
                  placeholder="e.g. 5e1a3b11-..."
                  className="w-full bg-base border border-panel-light rounded-lg py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-foreground placeholder-foreground-muted/50 transition-all"
                  value={chapterId}
                  onChange={(e) => setChapterId(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !chapterId.trim()}
              className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin mr-2" size={18} />
                  Starting...
                </>
              ) : (
                'Start Reading'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
