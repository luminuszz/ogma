import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ArrowLeft, Settings } from 'lucide-react';
import { useChapterStatus, useRetryChapter, useChapterNavigation, useChapterSSEListener } from '../hooks/useManga';
import { ReaderComponent } from '../components/ReaderComponent';
import { Loader } from '../components/Loader';
import { ProgressBar } from '../components/ProgressBar';
import { ErrorCard } from '../components/ErrorCard';
import { LoadingStatus } from '../components/LoadingStatus';
import { ReaderSettingsDrawer } from '../components/ReaderSettingsDrawer';
import { useReadSettings } from '@/hooks/useReadSettings';

export function Reader() {
  const navigate = useNavigate();
  const { chapterId } = useParams<{ chapterId: string }>();
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const { data: status, error: queryError, isFetching } = useChapterStatus(chapterId);
  useChapterSSEListener(chapterId, status);

  const { readingDirection, imageFit, loadingMode } = useReadSettings();
  const retryMutation = useRetryChapter();

  const handleNavigateHome = () => navigate('/');
  const handleOpenSettings = () => setIsSettingsOpen(true);
  const handleCloseSettings = () => setIsSettingsOpen(false);

  const handleRetry = () => {
    if (chapterId) {
      retryMutation.mutate(chapterId, {
        onSuccess: () => {
          toast.success('Páginas sendo recarregadas!');
        }
      });
    }
  };

  const isPolling = isFetching;
  const error = queryError?.message || (status?.status === 'error' ? status.error : null);

  const { currentChapterData, prevChapterId, nextChapterId } = useChapterNavigation(chapterId);

  const currentChapterTitle = currentChapterData ?
    `${currentChapterData.title} - Capitulo: ${currentChapterData.chapter.padStart(2, '0')}`
    : chapterId;

  const fetchedPages = useMemo(() => {
    if(!status || !status?.readyPages) return []

    return status.readyPages
      .toSorted((a, b) => a.pageIndex - b.pageIndex)
      .map(page => page.url);
  }, [status]);

  const pages = loadingMode === 'wait' && isPolling ? [] : fetchedPages;
  const totalPages = status?.total || pages.length;
  const progressPercent = totalPages > 0 ? ((currentPageIndex + 1) / totalPages) * 100 : 0;

  const handleNextChapter = () => {
    if (nextChapterId) {
      navigate(`/reader/${nextChapterId}`);
    }
  };

  const handlePrevChapter = () => {
    if (prevChapterId) {
      navigate(`/reader/${prevChapterId}`);
    }
  };


  useEffect(() => {
    setCurrentPageIndex(0);
    window.scrollTo(0, 0);
  }, [chapterId]);

  useEffect(() => {
    if (currentChapterTitle) {
      document.title =  currentChapterTitle
    }

    return () => {
      document.title = `Ogma | web`
    }

  } , [currentChapterTitle])






  return (
    <div className="flex-1 flex flex-col bg-black min-h-screen relative pb-16">
      <div className="sticky top-16 z-40 bg-panel/80 backdrop-blur-md border-b border-panel-light p-2 px-4 flex items-center justify-between">
        <button
          onClick={handleNavigateHome}
          className="flex items-center text-foreground-muted hover:text-foreground transition-colors p-2 rounded-lg hover:bg-panel-light"
        >
          <ArrowLeft size={20} className="mr-2" />
          Voltar
        </button>
        <div className="text-sm font-medium truncate max-w-50 md:max-w-md text-foreground">
          {currentChapterTitle}
        </div>
        <button
          onClick={handleOpenSettings}
          className="p-2 text-foreground-muted hover:text-foreground transition-colors rounded-lg hover:bg-panel-light"
        >
          <Settings size={20} />
        </button>
      </div>

      <div className="flex-1 flex flex-col items-center">
        {error ? (
          <div className="flex flex-col items-center gap-4 mt-8">
            <ErrorCard error={error} onRetry={handleNavigateHome} />
            <button
              onClick={handleRetry}
              disabled={retryMutation.isPending}
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-lg font-medium transition-colors"
            >
              {retryMutation.isPending ? 'Recarregando...' : 'Recarregar páginas com erro'}
            </button>
          </div>
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
          <div className="flex items-center justify-between p-3 px-4 text-sm font-medium text-foreground">
            <button
              disabled={!prevChapterId}
              onClick={handlePrevChapter}
              className="px-3 py-1 rounded-md text-foreground-muted hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>
            <span>
              Página {currentPageIndex + 1} / {totalPages}
            </span>
            <button
              disabled={!nextChapterId}
              onClick={handleNextChapter}
              className="px-3 py-1 rounded-md text-foreground-muted hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Próximo
            </button>
          </div>
        </div>
      )}

      {/* Settings Drawer */}
      <ReaderSettingsDrawer
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
      />
    </div>
  );
}
