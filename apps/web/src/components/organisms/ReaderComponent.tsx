import React, { useState, useEffect } from 'react';
import { useInView } from 'react-intersection-observer';

interface ReaderProps {
  chapterId: string;
  pages: string[];
  onPageVisible?: (index: number) => void;
  readingDirection?: 'webtoon' | 'paged';
  imageFit?: 'width' | 'height';
}

const ReaderPage: React.FC<{ page: string; index: number; onVisible?: (idx: number) => void; imageFit: 'width' | 'height' }> = ({ page, index, onVisible, imageFit }) => {
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
        src={page}
        alt={`Page ${index + 1}`}
        className={`block object-contain ${imageFit === 'height' ? 'max-h-screen' : 'w-full max-w-4xl'}`}
        loading="lazy"
      />
    </div>
  );
};

export const ReaderComponent: React.FC<ReaderProps> = ({ pages, onPageVisible, readingDirection = 'webtoon', imageFit = 'width' }) => {
  const [pagedIndex, setPagedIndex] = useState(0);

  useEffect(() => {
    if (readingDirection === 'paged' && onPageVisible) {
      onPageVisible(pagedIndex);
    }
  }, [pagedIndex, readingDirection, onPageVisible]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (readingDirection !== 'paged') return;
      if (e.key === 'ArrowLeft') {
        setPagedIndex(prev => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowRight') {
        setPagedIndex(prev => Math.min(pages.length - 1, prev + 1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [readingDirection, pages.length]);

  const handleTouch = (e: React.MouseEvent<HTMLDivElement>) => {
    if (readingDirection !== 'paged') return;
    const { clientX } = e;
    const { innerWidth } = window;
    if (clientX < innerWidth / 2) {
      setPagedIndex(prev => Math.max(0, prev - 1));
    } else {
      setPagedIndex(prev => Math.min(pages.length - 1, prev + 1));
    }
  };

  if (!pages || pages.length === 0) {
    return <div className="text-center text-foreground-muted py-8">No pages to display</div>;
  }

  if (readingDirection === 'paged') {
    return (
      <div 
        className="w-full h-[calc(100vh-120px)] flex justify-center items-center bg-black cursor-pointer select-none overflow-hidden relative"
        onClick={handleTouch}
      >
        <img
          src={pages[pagedIndex]}
          alt={`Page ${pagedIndex + 1}`}
          className={`block object-contain ${imageFit === 'height' ? 'max-h-full' : 'w-full'}`}
        />
        {/* Transparent overlays to ensure click areas work over the image */}
        <div className="absolute top-0 bottom-0 left-0 w-1/2 z-10" />
        <div className="absolute top-0 bottom-0 right-0 w-1/2 z-10" />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-0 w-full bg-black">
      {pages.map((page, idx) => (
        <ReaderPage 
          key={page} 
           
          page={page} 
          index={idx} 
          onVisible={onPageVisible}
          imageFit={imageFit}
        />
      ))}
    </div>
  );
};
