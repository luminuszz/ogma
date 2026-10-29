import toast from "react-hot-toast";
import { Link } from 'react-router-dom';
import { Trash2, Loader2, RotateCw, Clock } from 'lucide-react';
import { useDeleteChapter, useRetryChapter } from '@/hooks/useManga';

interface LibraryCardProps {
  id: string;
  chapter: string;
  downloaded: number;
  total: number;
  status: string;
}

export const LibraryCard = ({ id, chapter, downloaded, total, status }: LibraryCardProps) => {
  const deleteChapter = useDeleteChapter();
  const retryChapter = useRetryChapter();

  const handleDelete = () => {
    if (window.confirm("Tem certeza que deseja deletar este capítulo? Ele será removido permanentemente da nuvem.")) {
      deleteChapter.mutate(id, {
        onSuccess: () => {
          toast.success('Capítulo deletado com sucesso!');
        },
        onError: () => {
          toast.error('Erro ao deletar capítulo.');
        }
      });
    }
  };

  const handleRetry = () => {
    retryChapter.mutate(id, {
      onSuccess: () => {
        toast.success('Páginas enviadas para a fila novamente!');
      },
      onError: () => {
        toast.error('Erro ao recarregar as páginas.');
      }
    });
  };

  const isError = status === 'error';
  const isPending = status === 'pending';
  const isProcessing = status === 'processing';
  const progressPercent = total > 0 ? Math.round((downloaded / total) * 100) : 0;
  const remainingPages = Math.max(0, total - downloaded);

  return (
    <div className={`w-full min-h-20 sm:h-20 bg-base rounded-2xl px-6 py-3 sm:py-0 flex flex-wrap sm:flex-nowrap justify-between items-center gap-4 border ${isProcessing ? 'border-primary/50 shadow-[0_0_15px_rgba(var(--color-primary),0.1)]' : isPending ? 'border-panel-light' : isError ? 'border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'border-panel-light hover:border-primary/50'} transition-colors`}>
      <div className="flex gap-6 items-center">
        <span className="text-foreground-muted font-bold text-lg shrink-0">Ch. {chapter}</span>
        <div className="flex flex-col gap-1">
          {isProcessing ? (
            <div className="flex flex-col">
              <div className="flex items-center gap-2 text-primary text-sm font-medium">
                <Loader2 size={14} className="animate-spin shrink-0" />
                <span>Traduzindo... {total > 0 ? `${progressPercent}% (${downloaded}/${total})` : 'Iniciando'}</span>
              </div>
              <div 
                role="progressbar"
                aria-label="Progresso da tradução"
                aria-valuenow={progressPercent}
                aria-valuemin={0}
                aria-valuemax={100}
                className="w-32 sm:w-44 h-1.5 bg-panel-light rounded-full overflow-hidden mt-1"
              >
                <div 
                  className="bg-primary h-full transition-all duration-300"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          ) : isPending ? (
            <div className="flex items-center gap-2 text-foreground-muted text-sm font-medium">
              <Clock size={14} />
              <span>Na fila de espera</span>
            </div>
          ) : isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm font-medium">
              {downloaded > 0 ? (
                <span>Pausado na pág. {downloaded + 1}/{total} • {remainingPages} restantes</span>
              ) : (
                <span>Erro na tradução ({downloaded}/{total})</span>
              )}
            </div>
          ) : (
            <span className="text-foreground-muted text-sm font-normal">
              Traduzido: {downloaded}/{total} páginas • PT-BR
            </span>
          )}
        </div>
      </div>
      
      <div className="flex items-center gap-3 shrink-0">
        {isError && (
          <button 
            onClick={handleRetry}
            disabled={retryChapter.isPending}
            className="h-10 px-4 flex justify-center items-center rounded-full text-red-500 hover:text-white hover:bg-red-500 transition-colors border border-red-500/30 font-medium text-sm gap-2"
            title={downloaded > 0 ? `Retomar (${remainingPages} restam)` : 'Recarregar páginas com erro'}
          >
            {retryChapter.isPending ? <Loader2 size={16} className="animate-spin" /> : <RotateCw size={16} />}
            {downloaded > 0 ? `Retomar (${remainingPages} restam)` : 'Tentar Novamente'}
          </button>
        )}
        <button 
          onClick={handleDelete}
          disabled={deleteChapter.isPending}
          className="h-10 w-10 flex justify-center items-center rounded-full text-foreground-muted hover:text-red-500 hover:bg-red-500/10 transition-colors"
          title="Deletar Capítulo"
        >
          {deleteChapter.isPending ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={18} />}
        </button>
        <Link 
          to={`/reader/${id}`}
          className="h-10 bg-[#333333] hover:bg-[#444] rounded-full px-6 flex justify-center items-center transition-colors"
        >
          <span className="text-foreground font-semibold text-sm">Ler</span>
        </Link>
      </div>
    </div>
  );
};
