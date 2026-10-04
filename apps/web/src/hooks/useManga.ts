import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import type { ChapterStatus, LibraryManga } from '@/api';

export const useLibrary = () => {
  return useQuery<LibraryManga[], Error>({
    queryKey: ['library'],
    queryFn: api.getLibrary,
  });
};

export const useStartDownload = () => {
  return useMutation({
    mutationFn: api.startDownload,
  });
};

export const useStartBulkDownload = () => {
  return useMutation({
    mutationFn: api.startBulkDownload,
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
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'done' || data?.status === 'error') {
        return false;
      }
      return 2000;
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
