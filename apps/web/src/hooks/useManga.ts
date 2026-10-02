import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api';
import type { ChapterStatus } from '@/api';

export const useStartDownload = () => {
  return useMutation({
    mutationFn: api.startDownload,
  });
};

export const useChapterStatus = (chapterId: string | undefined, isPolling: boolean) => {
  return useQuery<ChapterStatus, Error>({
    queryKey: ['chapterStatus', chapterId],
    queryFn: () => {
      if (!chapterId) throw new Error("No chapter ID");
      return api.getStatus(chapterId);
    },
    enabled: !!chapterId,
    refetchInterval: isPolling ? 1000 : false,
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
