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
  status: string;
};

export interface ScraperChapterItem {
  id: string;
  number: string;
  title?: string;
  url: string;
}

export interface ExistingMangaSummary {
  id: string;
  title: string;
  existingChapterNumbers: string[];
}

export interface ScraperPreviewResponse {
  supported: boolean;
  provider: string;
  mangaId: string;
  title: string;
  coverUrl?: string;
  chapters: ScraperChapterItem[];
  existingWorks?: ExistingMangaSummary[];
  suggestedMangaId?: string | null;
}

export interface ScraperStartPayload {
  provider: string;
  mangaId: string;
  title: string;
  chapters: ScraperChapterItem[];
  forceTranslate?: boolean;
}

export interface OpenRouterCredits {
  enabled: boolean;
  remaining: number;
  usage_daily: number;
  usage_total: number;
  limit?: number | null;
  error?: string;
}

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

  retryChapter: async (chapterId: string): Promise<void> => {
    const res = await fetch(`/api/manga/${chapterId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      throw new Error('Failed to retry chapter');
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

  previewScraper: async (url: string): Promise<ScraperPreviewResponse> => {
    const res = await fetch('/api/scraper/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao buscar prévia da obra');
    }
    return res.json();
  },

  startScraper: async (payload: ScraperStartPayload): Promise<{ status: string; count: number }> => {
    const res = await fetch('/api/scraper/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao iniciar scraping');
    }
    return res.json();
  },

  getOpenRouterCredits: async (): Promise<OpenRouterCredits> => {
    const res = await fetch('/api/openrouter/credits');
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Falha ao buscar créditos do OpenRouter');
    }
    return res.json();
  },
};
