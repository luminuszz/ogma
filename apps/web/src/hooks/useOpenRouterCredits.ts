import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export interface OpenRouterCredits {
  enabled: boolean;
  remaining: number;
  usage_daily: number;
  usage_total: number;
  limit?: number | null;
  error?: string;
}

export const fetchOpenRouterCredits = async (): Promise<OpenRouterCredits> => {
  return api.getOpenRouterCredits();
};

export const useOpenRouterCredits = () => {
  const query = useQuery<OpenRouterCredits, Error>({
    queryKey: ['openrouter-credits'],
    queryFn: fetchOpenRouterCredits,
    staleTime: 30000,
  });

  return {
    ...query,
    data: query.data,
    refetch: query.refetch,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
  };
};
