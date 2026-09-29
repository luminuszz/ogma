import React from 'react';

interface ReaderProps {
  chapterId: string;
  pages: string[];
}

export const Reader: React.FC<ReaderProps> = ({ chapterId, pages }) => {
  if (!pages || pages.length === 0) {
    return <div>No pages to display</div>;
  }

  return (
    <div className="reader">
      {pages.map((page, idx) => (
        <div key={page} className="reader-page" style={{ marginBottom: '1rem', textAlign: 'center' }}>
          <img
            src={`/data/${chapterId}/${page}`}
            alt={`Page ${idx + 1}`}
            style={{ maxWidth: '100%', height: 'auto' }}
            loading="lazy"
          />
        </div>
      ))}
    </div>
  );
};
