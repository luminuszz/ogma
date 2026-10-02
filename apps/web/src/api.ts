export type ChapterStatus = {
  status: 'not_found' | 'processing' | 'done' | 'error';
  total?: number;
  completed?: number;
  failed?: number;
  error?: string;
  chapterId?: string;
  readyPages?: { pageIndex: number; url: string }[];
};

export type LibraryManga = {
  id: string;
  title: string;
  chapter: string;
  downloaded: number;
  total: number;
};

export const api = {
  getLibrary: async (): Promise<LibraryManga[]> => {
    const res = await fetch('/api/manga/library');
    if (!res.ok) throw new Error('Failed to get library');
    const data = await res.json();
    return data.library;
  },

  startDownload: async (chapterId: string): Promise<void> => {
    const res = await fetch(`/api/manga/${chapterId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      throw new Error('Failed to start download');
    }
  },

  getStatus: async (chapterId: string): Promise<ChapterStatus> => {
    const res = await fetch(`/api/manga/${chapterId}/status`);
    if (!res.ok) {
      throw new Error('Failed to get status');
    }
    return res.json();
  },

  clearCache: async (): Promise<void> => {
    const res = await fetch('/api/admin/clear-cache', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      throw new Error('Failed to clear cache');
    }
  },
};
