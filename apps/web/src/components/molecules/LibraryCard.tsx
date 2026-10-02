import { Link } from 'react-router-dom';

interface LibraryCardProps {
  id: string;
  title: string;
  chapter: string;
  downloaded: number;
  total: number;
}

export const LibraryCard = ({ id, title, chapter, downloaded, total }: LibraryCardProps) => {
  return (
    <div className="w-full h-20 bg-base rounded-2xl px-6 flex justify-between items-center border border-panel-light hover:border-primary/50 transition-colors">
      <div className="flex gap-6 items-center">
        <span className="text-foreground-muted font-bold text-lg">Ch. {chapter}</span>
        <div className="flex flex-col gap-1">
          <span className="text-foreground font-semibold text-base">{title || "Unknown Title"}</span>
          <span className="text-foreground-muted text-sm font-normal">
            Baixado: {downloaded}/{total} páginas • PT-BR
          </span>
        </div>
      </div>
      
      <Link 
        to={`/reader/${id}`}
        className="h-10 bg-[#333333] hover:bg-[#444] rounded-full px-6 flex justify-center items-center transition-colors"
      >
        <span className="text-foreground font-semibold text-sm">Ler</span>
      </Link>
    </div>
  );
};
