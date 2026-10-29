import { useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import type { ChapterStatus, LibraryManga } from '@/api';

export const useLibrary = (disablePolling = false) => {
  return useQuery<LibraryManga[], Error>({
    queryKey: ['library'],
    queryFn: api.getLibrary,
    staleTime: 1000 * 5, // 5 segundos
    refetchInterval: disablePolling ? false : (query) => {
      const data = query.state.data;
      if (!data) return 5000;
      const hasActive = data.some(item => item.status === 'processing' || item.status === 'pending');
      return hasActive ? 2000 : 10000;
    }
  });
};

export const useStartDownload = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.startDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
};

export const useStartBulkDownload = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.startBulkDownload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
};

export const useDeleteChapter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
};

export const useChapterStatus = (chapterId: string | undefined) => {
  return useQuery<ChapterStatus, Error>({
    queryKey: ['chapterStatus', chapterId],
    queryFn: () => {
      if (!chapterId) throw new Error("No chapter ID");
      return api.getStatus(chapterId);
    },
    enabled: !!chapterId,
  });
};

export const useRetryChapter = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.retryChapter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapterStatus'] });
      queryClient.invalidateQueries({ queryKey: ['library'] });
    },
  });
};

export const useClearCache = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearCache,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapterStatus'] });
    },
  });
};

export const useChapterNavigation = (chapterId: string | undefined) => {
  const { data: library } = useLibrary(true);

  return useMemo(() => {
    const currentChapterData = library?.find((item) => item.id === chapterId);
    
    if (!library || !currentChapterData) {
      return { currentChapterData: null, prevChapterId: null, nextChapterId: null };
    }

    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

    const mangaChapters = library
      .filter((item) => item.title === currentChapterData.title)
      .toSorted((a, b) => collator.compare(a.chapter, b.chapter));

    const currentIndex = mangaChapters.findIndex((item) => item.id === chapterId);

    return {
      currentChapterData,
      prevChapterId: mangaChapters[currentIndex - 1]?.id || null,
      nextChapterId: mangaChapters[currentIndex + 1]?.id || null,
    };
  }, [library, chapterId]);
};

export const useChapterSSEListener = (chapterId: string | undefined, status: ChapterStatus | undefined) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!chapterId || !status || status.status === 'done' || status.status === 'error') return;
    if (typeof EventSource === 'undefined') return;

    const evtSource = new EventSource(`/api/manga/${chapterId}/stream`);

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        queryClient.setQueryData(['chapterStatus', chapterId], (old: any) => {
          if (!old) return old;
          const newReadyPages = [...(old.readyPages || [])];
          if (!newReadyPages.some((p: any) => p.url === data.url)) {
            newReadyPages.push({ url: data.url, pageIndex: data.pageIndex });
          }
          return {
            ...old,
            readyPages: newReadyPages,
            completed: Math.max(old.completed || 0, data.pageIndex + 1),
          };
        });
        queryClient.invalidateQueries({ queryKey: ['openrouter-credits'] });
      } catch (err) {
        console.error('SSE Error:', err);
      }
    };

    return () => {
      evtSource.close();
    };
  }, [chapterId, status?.status, queryClient]);
};
