import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Settings, X } from 'lucide-react';
import { api, type ChapterStatus } from '../api';
import { Reader as ReaderComponent } from '../components/Reader';

export function Reader() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();
  
  const [status, setStatus] = useState<ChapterStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pages, setPages] = useState<string[]>([]);
  const [isPolling, setIsPolling] = useState(true);

  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    if (!chapterId || !isPolling) return;

    let timeoutId: number;
    let isMounted = true;

    const poll = async () => {
      try {
        const res = await api.getStatus(chapterId);
        if (!isMounted) return;
        setStatus(res);

        if (res.status === 'completed' && res.pages) {
          setIsPolling(false);
          setPages(res.pages);
        } else if (res.status === 'error') {
          setIsPolling(false);
          setError(res.error || 'Failed to download chapter');
        } else {
          timeoutId = window.setTimeout(poll, 2000);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setIsPolling(false);
        setError(err.message || 'Failed to get status');
      }
    };

    poll();

    return () => {
      isMounted = false;
      window.clearTimeout(timeoutId);
    };
  }, [chapterId, isPolling]);

  const totalPages = pages.length;
  const progressPercent = totalPages > 0 ? ((currentPageIndex + 1) / totalPages) * 100 : 0;

  return (
    <div className="flex-1 flex flex-col bg-black min-h-screen relative pb-16">
      <div className="sticky top-16 z-40 bg-panel/80 backdrop-blur-md border-b border-panel-light p-2 px-4 flex items-center justify-between">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center text-foreground-muted hover:text-foreground transition-colors p-2 rounded-lg hover:bg-panel-light"
        >
          <ArrowLeft size={20} className="mr-2" />
          Back
        </button>
        <div className="text-sm font-medium truncate max-w-[200px] md:max-w-md text-foreground">
          {chapterId}
        </div>
        <button 
          onClick={() => setIsSettingsOpen(true)}
          className="p-2 text-foreground-muted hover:text-foreground transition-colors rounded-lg hover:bg-panel-light"
        >
          <Settings size={20} />
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center">
        {error ? (
          <div className="mt-10 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-center max-w-md">
            <p className="font-semibold mb-2">Error</p>
            <p className="text-sm">{error}</p>
            <button 
              onClick={() => navigate('/')}
              className="mt-4 px-4 py-2 bg-panel-light hover:bg-panel rounded-lg text-foreground transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : isPolling ? (
          <div className="mt-20 flex flex-col items-center text-foreground-muted">
            <Loader2 size={32} className="animate-spin mb-4 text-primary" />
            <p>
              {status?.status === 'downloading' 
                ? `Downloading... ${status.progress || 0} / ${status.total || '?'}`
                : 'Loading chapter...'}
            </p>
          </div>
        ) : (
          <div className="w-full">
            {chapterId && totalPages > 0 ? (
              <ReaderComponent 
                chapterId={chapterId} 
                pages={pages} 
                onPageVisible={setCurrentPageIndex}
              />
            ) : (
              <div className="mt-10 text-center text-foreground-muted">No pages found.</div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Progress Bar */}
      {totalPages > 0 && !isPolling && !error && (
        <div className="fixed bottom-0 left-0 right-0 bg-panel border-t border-panel-light z-40">
          <div className="h-1 w-full bg-base">
            <div 
              className="h-full bg-primary transition-all duration-300 ease-out" 
              style={{ width: `${progressPercent}%` }} 
            />
          </div>
          <div className="flex items-center justify-center p-3 text-sm font-medium text-foreground">
            Page {currentPageIndex + 1} / {totalPages}
          </div>
        </div>
      )}

      {/* Settings Drawer */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div 
            className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity" 
            onClick={() => setIsSettingsOpen(false)}
          />
          <div className="relative w-80 bg-panel h-full border-l border-panel-light flex flex-col shadow-2xl animate-fade-in-right">
            <div className="p-4 flex items-center justify-between border-b border-panel-light">
              <h3 className="font-semibold text-lg">Settings</h3>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                className="p-2 text-foreground-muted hover:text-foreground rounded-lg hover:bg-panel-light transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 flex-1 overflow-y-auto space-y-8">
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Reading Direction</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button className="bg-primary/20 border border-primary text-primary py-2 px-3 rounded-lg text-sm font-medium">
                    Webtoon
                  </button>
                  <button className="bg-base border border-panel-light text-foreground-muted hover:text-foreground py-2 px-3 rounded-lg text-sm font-medium transition-colors">
                    Paged (LTR)
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Image Fit</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button className="bg-primary/20 border border-primary text-primary py-2 px-3 rounded-lg text-sm font-medium">
                    Width
                  </button>
                  <button className="bg-base border border-panel-light text-foreground-muted hover:text-foreground py-2 px-3 rounded-lg text-sm font-medium transition-colors">
                    Height
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
