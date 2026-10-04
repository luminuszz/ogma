import { Link } from 'react-router-dom';
import { Trash2, Loader2 } from 'lucide-react';
import { useDeleteChapter } from '@/hooks/useManga';

interface LibraryCardProps {
  id: string;
  chapter: string;
  downloaded: number;
  total: number;
}

export const LibraryCard = ({ id, chapter, downloaded, total }: LibraryCardProps) => {
  const deleteChapter = useDeleteChapter();

  const handleDelete = () => {
    if (confirm("Tem certeza que deseja deletar este capítulo? Ele será removido localmente e da nuvem.")) {
      deleteChapter.mutate(id);
    }
  };

  return (
    <div className="w-full h-20 bg-base rounded-2xl px-6 flex justify-between items-center border border-panel-light hover:border-primary/50 transition-colors">
      <div className="flex gap-6 items-center">
        <span className="text-foreground-muted font-bold text-lg">Ch. {chapter}</span>
        <div className="flex flex-col gap-1">
          <span className="text-foreground-muted text-sm font-normal">
            Baixado: {downloaded}/{total} páginas • PT-BR
          </span>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
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
