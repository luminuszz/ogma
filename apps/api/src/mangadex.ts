import { Effect } from 'effect';

export interface MangaDexAtHomeResponse {
  baseUrl: string;
  chapter: {
    hash: string;
    data: string[];
    dataSaver: string[];
  };
}

export interface PageInfo {
  url: string;
  pageIndex: number;
  filename: string;
}

/**
 * Fetches the at-home server info for a given chapter from MangaDex API.
 * Returns the base URL and image file list.
 */
export const fetchChapterPages = (chapterId: string): Effect.Effect<PageInfo[], Error> =>
  Effect.tryPromise({
    try: async () => {
      const res = await fetch(`https://api.mangadex.org/at-home/server/${chapterId}`);

      if (!res.ok) {
        throw new Error(`MangaDex API error: ${res.status} ${res.statusText}`);
      }

      const data: MangaDexAtHomeResponse = await res.json();

      return data.chapter.data.map((filename, index) => ({
        url: `${data.baseUrl}/data/${data.chapter.hash}/${filename}`,
        pageIndex: index,
        filename,
      }));
    },
    catch: (err) => new Error(`Failed to fetch chapter pages: ${err}`),
  });
