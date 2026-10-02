export type ChapterStatus = {
  status: 'not_found' | 'processing' | 'done' | 'error';
  total?: number;
  completed?: number;
  failed?: number;
  error?: string;
  chapterId?: string;
  readyPages?: number[]
};

export type LibraryManga = {
  id: string;
  title: string;
  chapter: string;
  downloaded: boolean;
  total: number;
};

export const api = {
  getLibrary: async (): Promise<LibraryManga[]> => {
    return [
      { id: '1', title: 'One Piece', chapter: '1090', downloaded: true, total: 17 },
      { id: '2', title: 'Jujutsu Kaisen', chapter: '230', downloaded: false, total: 19 },
      { id: '3', title: 'Chainsaw Man', chapter: '140', downloaded: true, total: 21 },
    ];
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
