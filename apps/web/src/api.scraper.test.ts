import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './api';

describe('Scraper API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls previewScraper with url and returns data', async () => {
    const mockResponse = {
      supported: true,
      provider: 'lycantoons',
      mangaId: 'lycantoons:test',
      title: 'Test Manga',
      chapters: []
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const res = await api.previewScraper('https://lycantoons.com/series/test');
    expect(global.fetch).toHaveBeenCalledWith('/api/scraper/preview', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ url: 'https://lycantoons.com/series/test' })
    }));
    expect(res).toEqual(mockResponse);
  });
});
