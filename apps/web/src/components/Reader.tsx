import React from 'react';

interface ReaderProps {
  chapterId: string;
  pages: string[];
}

export const Reader: React.FC<ReaderProps> = ({ chapterId, pages }) => {
  if (!pages || pages.length === 0) {
    return <div className="text-center text-foreground-muted py-8">No pages to display</div>;
  }

  return (
    <div className="flex flex-col items-center gap-4 py-4 w-full">
      {pages.map((page, idx) => (
        <div key={page} className="w-full flex justify-center">
          <img
            src={`/data/${chapterId}/${page}`}
            alt={`Page ${idx + 1}`}
            className="max-w-full h-auto object-contain"
            loading="lazy"
          />
        </div>
      ))}
    </div>
  );
};
