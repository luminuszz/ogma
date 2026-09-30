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

export interface MangaChapter {
  id: string;
  chapter: string | null;
  title: string | null;
  language: string | null;
}

export const fetchMangaFeed = (mangaId: string): Effect.Effect<MangaChapter[], Error> =>
  Effect.tryPromise({
    try: async () => {
      const langs = 'translatedLanguage[]=en&translatedLanguage[]=pt-br&translatedLanguage[]=pt&translatedLanguage[]=es-la&translatedLanguage[]=es';
      const res = await fetch(`https://api.mangadex.org/manga/${mangaId}/feed?order[chapter]=desc&limit=100&${langs}`);

      if (!res.ok) {
        throw new Error(`MangaDex API error: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();

      return data.data.map((item: any) => ({
        id: item.id,
        chapter: item.attributes.chapter,
        title: item.attributes.title,
        language: item.attributes.translatedLanguage,
      }));
    },
    catch: (err) => new Error(`Failed to fetch manga chapters: ${err}`),
  });
