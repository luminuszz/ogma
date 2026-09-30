import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2 } from 'lucide-react';
import { api } from '../api';

export function Home() {
  const [inputUrl, setInputUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const navigate = useNavigate();

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;

    setError(null);
    setIsLoading(true);

    try {
      const uuidMatch = inputUrl.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
      const extractedId = uuidMatch ? uuidMatch[0] : inputUrl.trim();

      if (inputUrl.includes('/title/') || chapters.length > 0) {
        // It's a Manga URL, fetch chapters
        const res = await fetch(`/api/manga/${extractedId}/chapters`);
        if (!res.ok) throw new Error('Failed to fetch chapters');
        const data = await res.json();
        setChapters(data.chapters);
      } else {
        // Assume it's a Chapter ID/URL
        await api.startDownload(extractedId);
        navigate(`/reader/${encodeURIComponent(extractedId)}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to process request');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-panel rounded-2xl shadow-xl overflow-hidden border border-panel-light">
        <div className="p-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold mb-2">Read Manga</h2>
            <p className="text-foreground-muted text-sm">
              Enter a MangaDex Chapter ID or Manga URL.
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
                  placeholder="https://mangadex.org/title/..."
                  className="w-full bg-base border border-panel-light rounded-lg py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-foreground placeholder-foreground-muted/50 transition-all"
                  value={inputUrl}
                  onChange={(e) => setInputUrl(e.target.value)}
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
              disabled={isLoading || !inputUrl.trim()}
              className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <><Loader2 className="animate-spin mr-2" size={18} /> Processing...</>
              ) : (
                chapters.length > 0 ? 'Refresh Chapters' : 'Start / Fetch'
              )}
            </button>
          </form>
        </div>
      </div>

      {chapters.length > 0 && (
        <div className="w-full max-w-2xl mt-6 bg-panel rounded-2xl shadow-xl border border-panel-light p-6 animate-fade-in-up">
          <h3 className="font-semibold text-lg mb-4">Found {chapters.length} chapters</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
            {chapters.map((ch: any, idx: number) => (
              <div key={ch.id} className="flex items-center justify-between p-3 bg-base rounded-lg border border-panel-light hover:border-primary/50 transition-colors">
                <div>
                  <div className="font-medium text-foreground flex items-center gap-2">
                    Chapter {ch.chapter || '?'}
                    {ch.language && (
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-panel-light text-foreground-muted border border-panel-light/50">
                        {ch.language}
                      </span>
                    )}
                  </div>
                  {ch.title && <div className="text-sm text-foreground-muted">{ch.title}</div>}
                </div>
                <button
                  onClick={async () => {
                    await api.startDownload(ch.id);
                    navigate(`/reader/${ch.id}`);
                  }}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${idx === 0 ? 'bg-primary text-white hover:bg-primary/90' : 'bg-panel-light text-foreground hover:bg-panel-light/80'}`}
                >
                  Read
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
