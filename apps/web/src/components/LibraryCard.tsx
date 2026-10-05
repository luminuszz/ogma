import toast from "react-hot-toast";
import { Link } from 'react-router-dom';
import { Trash2, Loader2, RotateCw } from 'lucide-react';
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
  // Note: if status is processing and downloaded < total, it will show "Traduzindo..."
  const isActuallyTranslating = (total === 0 || downloaded < total) && status !== 'error';
  const progressPercent = total > 0 ? Math.round((downloaded / total) * 100) : 0;

  return (
    <div className={`w-full h-20 bg-base rounded-2xl px-6 flex justify-between items-center border ${isActuallyTranslating ? 'border-primary/50 shadow-[0_0_15px_rgba(var(--color-primary),0.1)]' : isError ? 'border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'border-panel-light hover:border-primary/50'} transition-colors`}>
      <div className="flex gap-6 items-center">
        <span className="text-foreground-muted font-bold text-lg">Ch. {chapter}</span>
        <div className="flex flex-col gap-1">
          {isActuallyTranslating ? (
            <div className="flex items-center gap-2 text-primary text-sm font-medium">
              <Loader2 size={14} className="animate-spin" />
              <span>Traduzindo... {total > 0 ? `${progressPercent}%` : 'Iniciando'}</span>
            </div>
          ) : isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm font-medium">
              <span>Erro na tradução ({downloaded}/{total})</span>
            </div>
          ) : (
            <span className="text-foreground-muted text-sm font-normal">
              Traduzido: {downloaded}/{total} páginas • PT-BR
            </span>
          )}
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        {isError && (
          <button 
            onClick={handleRetry}
            disabled={retryChapter.isPending}
            className="h-10 px-4 flex justify-center items-center rounded-full text-red-500 hover:text-white hover:bg-red-500 transition-colors border border-red-500/30 font-medium text-sm gap-2"
            title="Recarregar páginas com erro"
          >
            {retryChapter.isPending ? <Loader2 size={16} className="animate-spin" /> : <RotateCw size={16} />}
            Tentar Novamente
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
