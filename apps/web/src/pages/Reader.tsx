import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api, type ChapterStatus } from '../api';
import { Reader as ReaderComponent } from '../components/Reader';

export function Reader() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();
  
  const [status, setStatus] = useState<ChapterStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pages, setPages] = useState<string[]>([]);
  const [isPolling, setIsPolling] = useState(true);

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

  return (
    <div className="flex-1 flex flex-col bg-base">
      <div className="sticky top-16 z-40 bg-panel/80 backdrop-blur-md border-b border-panel-light p-2 px-4 flex items-center justify-between">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center text-foreground-muted hover:text-foreground transition-colors p-2 rounded-lg hover:bg-panel-light"
        >
          <ArrowLeft size={20} className="mr-2" />
          Back
        </button>
        <div className="text-sm font-medium truncate max-w-[200px] md:max-w-md">
          {chapterId}
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center p-4">
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
          <div className="w-full max-w-3xl">
            {chapterId && pages.length > 0 ? (
              <ReaderComponent chapterId={chapterId} pages={pages} />
            ) : (
              <div className="mt-10 text-center text-foreground-muted">No pages found.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
