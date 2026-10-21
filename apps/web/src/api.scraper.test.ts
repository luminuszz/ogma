import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, type ScraperStartPayload } from './api';

describe('Scraper API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('previewScraper', () => {
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://lycantoons.com/series/test' })
      }));
      expect(res).toEqual(mockResponse);
    });

    it('throws error with detail message on failed preview request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'URL não suportada' }),
      } as Response);

      await expect(api.previewScraper('https://invalid.com')).rejects.toThrow('URL não suportada');
    });

    it('throws default error message when json parsing fails on error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => { throw new Error('invalid json'); },
      } as Response);

      await expect(api.previewScraper('https://invalid.com')).rejects.toThrow('Falha ao buscar prévia da obra');
    });
  });

  describe('startScraper', () => {
    const payload: ScraperStartPayload = {
      provider: 'lycantoons',
      mangaId: 'lycantoons:test',
      title: 'Test Manga',
      chapters: [
        { id: 'c1', number: '1', title: 'Chapter 1', url: 'https://lycantoons.com/series/test/1' }
      ],
      forceTranslate: true
    };

    it('calls startScraper with payload and returns status', async () => {
      const mockResponse = { status: 'queued', count: 1 };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const res = await api.startScraper(payload);
      expect(global.fetch).toHaveBeenCalledWith('/api/scraper/start', expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }));
      expect(res).toEqual(mockResponse);
    });

    it('throws error with detail message on failed start request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Scraper failed to start' }),
      } as Response);

      await expect(api.startScraper(payload)).rejects.toThrow('Scraper failed to start');
    });

    it('throws default error message when json parsing fails on error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => { throw new Error('invalid json'); },
      } as Response);

      await expect(api.startScraper(payload)).rejects.toThrow('Falha ao iniciar scraping');
    });
  });
});
