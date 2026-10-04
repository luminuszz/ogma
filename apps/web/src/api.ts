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

  startDownload: async (params: { chapterId: string; sourceLang?: string }): Promise<void> => {
    const url = new URL(`/api/manga/${params.chapterId}`, window.location.origin);
    if (params.sourceLang) {
      url.searchParams.append('source_lang', params.sourceLang);
    }
    const res = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      throw new Error('Failed to start download');
    }
  },

  startBulkDownload: async (params: { chapterIds: string[]; sourceLang?: string }): Promise<void> => {
    const res = await fetch('/api/manga/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chapterIds: params.chapterIds,
        sourceLang: params.sourceLang || 'auto',
      }),
    });
    if (!res.ok) {
      throw new Error('Failed to start bulk download');
    }
  },

  getStatus: async (chapterId: string): Promise<ChapterStatus> => {
    const res = await fetch(`/api/manga/${chapterId}/status`);
    if (!res.ok) {
      throw new Error('Failed to get status');
    }
    return res.json();
  },

  deleteChapter: async (chapterId: string): Promise<void> => {
    const res = await fetch(`/api/manga/${chapterId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error('Failed to delete chapter');
    }
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
