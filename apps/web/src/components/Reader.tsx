import React from 'react';
import { useInView } from 'react-intersection-observer';

interface ReaderProps {
  chapterId: string;
  pages: string[];
  onPageVisible?: (index: number) => void;
}

const ReaderPage: React.FC<{ chapterId: string; page: string; index: number; onVisible?: (idx: number) => void }> = ({ chapterId, page, index, onVisible }) => {
  const { ref, inView } = useInView({
    threshold: 0.1,
    rootMargin: "-10% 0px -10% 0px",
  });

  React.useEffect(() => {
    if (inView && onVisible) {
      onVisible(index);
    }
  }, [inView, index, onVisible]);

  return (
    <div ref={ref} className="w-full flex justify-center bg-black">
      <img
        src={`/data/${chapterId}/${page}`}
        alt={`Page ${index + 1}`}
        className="max-w-full h-auto object-contain block"
        loading="lazy"
      />
    </div>
  );
};

export const Reader: React.FC<ReaderProps> = ({ chapterId, pages, onPageVisible }) => {
  if (!pages || pages.length === 0) {
    return <div className="text-center text-foreground-muted py-8">No pages to display</div>;
  }

  return (
    <div className="flex flex-col items-center gap-0 w-full bg-black">
      {pages.map((page, idx) => (
        <ReaderPage 
          key={page} 
          chapterId={chapterId} 
          page={page} 
          index={idx} 
          onVisible={onPageVisible} 
        />
      ))}
    </div>
  );
};
