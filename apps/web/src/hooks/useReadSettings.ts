
import { useState, useEffect } from 'react';

export  type ReadingDirection = 'webtoon' | 'paged';
export  type ImageFit = 'width' | 'height';
export  type LoadingMode = 'real-time' | 'wait';

export function useReadSettings() {
  const [readingDirection, setReadingDirection] = useState<ReadingDirection>(
    localStorage.getItem('reader_direction') as any ?? 'rtl'
  );
  const [imageFit, setImageFit] = useState<ImageFit>(
    localStorage.getItem('reader_fit') as any ?? 'cover'
  );
  const [loadingMode, setLoadingMode] = useState<LoadingMode>(
    localStorage.getItem('reader_loading') as any ?? 'real-time'
  );

  useEffect(() => {
    localStorage.setItem('reader_direction', readingDirection);
    localStorage.setItem('reader_fit', imageFit);
    localStorage.setItem('reader_loading', loadingMode);
  }, [readingDirection, imageFit, loadingMode]);

  return {
    readingDirection,
    setReadingDirection,
    imageFit,
    setImageFit,
    loadingMode,
    setLoadingMode,
  };
}
