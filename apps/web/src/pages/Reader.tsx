import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Settings, X } from 'lucide-react';
import { api, type ChapterStatus } from '../api';
import { Reader as ReaderComponent } from '../components/Reader';

type ReadingDirection = 'webtoon' | 'paged';
type ImageFit = 'width' | 'height';
type LoadingMode = 'real-time' | 'wait';

export function Reader() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<ChapterStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedPages, setFetchedPages] = useState<string[]>([]);
  const [isPolling, setIsPolling] = useState(true);

  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const [readingDirection, setReadingDirection] = useState<ReadingDirection>(
    () => (localStorage.getItem('reader_direction') as ReadingDirection) || 'webtoon'
  );
  const [imageFit, setImageFit] = useState<ImageFit>(
    () => (localStorage.getItem('reader_fit') as ImageFit) || 'width'
  );
  const [loadingMode, setLoadingMode] = useState<LoadingMode>(
    () => (localStorage.getItem('reader_loading') as LoadingMode) || 'real-time'
  );

  useEffect(() => {
    localStorage.setItem('reader_direction', readingDirection);
    localStorage.setItem('reader_fit', imageFit);
    localStorage.setItem('reader_loading', loadingMode);
  }, [readingDirection, imageFit, loadingMode]);

  useEffect(() => {
    if (!chapterId || !isPolling) return;

    let timeoutId: number;
    let isMounted = true;

    const poll = async () => {
      try {
        const res = await api.getStatus(chapterId);
        if (!isMounted) return;
        setStatus(res);

        if (res.readyPages) {
          setFetchedPages(res.readyPages.map((i: number) => `${i}.png`));
        }
        if (res.status === 'done') {
          setIsPolling(false);
          if (!res.readyPages && res.total) {
            setFetchedPages(Array.from({ length: res.total }, (_, i) => `${i}.png`));
          }
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

  const pages = loadingMode === 'wait' && isPolling ? [] : fetchedPages;
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
          Voltar
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
            <p className="font-semibold mb-2">Erro</p>
            <p className="text-sm">{error}</p>
            <button
              onClick={() => navigate('/')}
              className="mt-4 px-4 py-2 bg-panel-light hover:bg-panel rounded-lg text-foreground transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        ) : isPolling && pages.length === 0 ? (
          <div className="mt-20 flex flex-col items-center gap-6 text-foreground-muted px-4 w-full max-w-sm mx-auto">
            <Loader2 size={40} className="animate-spin text-primary" />
            {status && status.total && status.total > 0 ? (
              <div className="w-full space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Traduzindo páginas...</span>
                  <span className="text-primary font-semibold">{status.completed ?? 0} / {status.total}</span>
                </div>
                <div className="w-full bg-panel-light rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.round(((status.completed ?? 0) / status.total) * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-center text-foreground-muted">
                  {status.total - (status.completed ?? 0)} página{(status.total - (status.completed ?? 0)) !== 1 ? 's' : ''} restante{(status.total - (status.completed ?? 0)) !== 1 ? 's' : ''}
                </p>
              </div>
            ) : (
              <p className="text-sm">Carregando capítulo...</p>
            )}
          </div>
        ) : (
          <div className="w-full">
            {chapterId && totalPages > 0 ? (
              <>
                <ReaderComponent
                  chapterId={chapterId}
                  pages={pages}
                  onPageVisible={setCurrentPageIndex}
                  readingDirection={readingDirection}
                  imageFit={imageFit}
                />
                {isPolling && (
                  <div className="flex flex-col items-center justify-center p-8 gap-4 text-foreground-muted">
                    <Loader2 size={30} className="animate-spin text-primary" />
                    <span className="text-sm">Traduzindo próximas páginas...</span>
                  </div>
                )}
              </>
            ) : (
              <div className="mt-10 text-center text-foreground-muted">Nenhuma página encontrada.</div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Progress Bar */}
      {totalPages > 0 && (!isPolling || loadingMode === 'real-time') && !error && (
        <div className="fixed bottom-0 left-0 right-0 bg-panel border-t border-panel-light z-40">
          <div className="h-1 w-full bg-base">
            <div
              className="h-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex items-center justify-center p-3 text-sm font-medium text-foreground">
            Página {currentPageIndex + 1} / {totalPages}
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
                  <button 
                    onClick={() => setReadingDirection('webtoon')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${readingDirection === 'webtoon' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Webtoon
                  </button>
                  <button 
                    onClick={() => setReadingDirection('paged')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${readingDirection === 'paged' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Paged (LTR)
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Image Fit</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => setImageFit('width')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${imageFit === 'width' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Width
                  </button>
                  <button 
                    onClick={() => setImageFit('height')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${imageFit === 'height' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Height
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Loading Mode</h4>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => setLoadingMode('real-time')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${loadingMode === 'real-time' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Real-time
                  </button>
                  <button 
                    onClick={() => setLoadingMode('wait')}
                    className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${loadingMode === 'wait' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
                  >
                    Wait all
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
