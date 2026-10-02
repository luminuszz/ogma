import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings, X } from 'lucide-react';
import { useChapterStatus } from '../hooks/useManga';
import { ReaderComponent } from '../components/organisms/ReaderComponent';
import { Loader } from '../components/atoms/Loader';
import { ProgressBar } from '../components/atoms/ProgressBar';
import { ErrorCard } from '../components/molecules/ErrorCard';
import { LoadingStatus } from '../components/molecules/LoadingStatus';

type ReadingDirection = 'webtoon' | 'paged';
type ImageFit = 'width' | 'height';
type LoadingMode = 'real-time' | 'wait';

export function Reader() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();

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

  const { data: status, error: queryError } = useChapterStatus(chapterId);
  const isPolling = status ? status.status !== 'done' && status.status !== 'error' : true;

  const error = queryError?.message || (status?.status === 'error' ? status.error : null);

  const fetchedPages = useMemo(() => {
    if (!status) return [];
    if (status.readyPages) {
      return status.readyPages
        .sort((a, b) => a.pageIndex - b.pageIndex)
        .map(page => page.url);
    }
    return [];
  }, [status]);

  const pages = loadingMode === 'wait' && isPolling ? [] : fetchedPages;
  const totalPages = status?.total || pages.length;
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
        <div className="text-sm font-medium truncate max-w-50 md:max-w-md text-foreground">
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
          <ErrorCard error={error} onRetry={() => navigate('/')} />
        ) : isPolling && pages.length === 0 ? (
          status && status.total && status.total > 0 ? (
            <LoadingStatus completed={status.completed ?? 0} total={status.total} />
          ) : (
            <div className="mt-20 flex justify-center w-full">
              <Loader message="Carregando capítulo..." />
            </div>
          )
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
                  <Loader message="Traduzindo próximas páginas..." />
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
          <ProgressBar percent={progressPercent} />
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
