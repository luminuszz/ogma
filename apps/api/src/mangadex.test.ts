import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Effect } from 'effect';
import { fetchChapterPages } from './mangadex.ts';

describe('MangaDex Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch and parse chapter pages from MangaDex API', async () => {
    const mockResponse = {
      baseUrl: 'https://uploads.mangadex.org',
      chapter: {
        hash: 'abc123',
        data: ['page1.png', 'page2.png', 'page3.png'],
        dataSaver: ['page1-saver.png', 'page2-saver.png', 'page3-saver.png'],
      },
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const pages = await Effect.runPromise(fetchChapterPages('test-chapter-id'));

    expect(pages).toHaveLength(3);
    expect(pages[0]).toEqual({
      url: 'https://uploads.mangadex.org/data/abc123/page1.png',
      pageIndex: 0,
      filename: 'page1.png',
    });
    expect(pages[2]).toEqual({
      url: 'https://uploads.mangadex.org/data/abc123/page3.png',
      pageIndex: 2,
      filename: 'page3.png',
    });

    expect(fetch).toHaveBeenCalledWith(
      'https://api.mangadex.org/at-home/server/test-chapter-id'
    );
  });

  it('should fail when MangaDex API returns non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(
      Effect.runPromise(fetchChapterPages('bad-chapter-id'))
    ).rejects.toThrow('Failed to fetch chapter pages');
  });

  it('should fail when fetch itself throws (network error)', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'));

    await expect(
      Effect.runPromise(fetchChapterPages('network-fail'))
    ).rejects.toThrow('Failed to fetch chapter pages');
  });
});
