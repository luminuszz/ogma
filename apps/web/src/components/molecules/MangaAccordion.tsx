import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { LibraryCard } from './LibraryCard';

interface MangaAccordionProps {
  mangaTitle: string;
  chapters: any[];
}

export const MangaAccordion = ({ mangaTitle, chapters }: MangaAccordionProps) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="flex flex-col border border-panel-light rounded-2xl overflow-hidden shadow-sm">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-5 bg-base hover:bg-panel/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <h3 className="text-xl font-bold text-foreground">{mangaTitle}</h3>
          <span className="text-sm font-medium text-foreground-muted bg-panel px-3 py-1 rounded-full">
            {chapters.length} {chapters.length === 1 ? 'capítulo' : 'capítulos'}
          </span>
        </div>
        <div className="text-foreground-muted bg-panel/50 p-2 rounded-full">
          {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </button>
      
      {isOpen && (
        <div className="p-5 flex flex-col gap-4 bg-panel/10 border-t border-panel-light">
          {chapters.map((item: any) => (
            <LibraryCard
              key={item.id}
              id={item.id}
              chapter={item.chapter}
              downloaded={typeof item.downloaded === 'boolean' ? (item.downloaded ? item.total : 0) : item.downloaded}
              total={item.total}
            />
          ))}
        </div>
      )}
    </div>
  );
};
