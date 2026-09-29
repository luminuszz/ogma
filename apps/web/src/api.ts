export type ChapterStatus = {
  status: 'idle' | 'queued' | 'downloading' | 'completed' | 'error';
  progress?: number;
  total?: number;
  pages?: string[];
  error?: string;
};

export const api = {
  startDownload: async (chapterId: string): Promise<void> => {
    const res = await fetch(`/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapterId }),
    });
    if (!res.ok) {
      throw new Error('Failed to start download');
    }
  },

  getStatus: async (chapterId: string): Promise<ChapterStatus> => {
    const res = await fetch(`/api/status/${chapterId}`);
    if (!res.ok) {
      throw new Error('Failed to get status');
    }
    return res.json();
  },
};
