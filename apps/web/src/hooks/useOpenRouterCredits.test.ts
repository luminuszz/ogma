import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useOpenRouterCredits, fetchOpenRouterCredits } from './useOpenRouterCredits';
import { api } from '../api';

describe('useOpenRouterCredits', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.restoreAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    React.createElement(QueryClientProvider, { client: queryClient }, children)
  );

  it('fetches credits using api.getOpenRouterCredits', async () => {
    const mockCredits = {
      enabled: true,
      remaining: 5.25,
      usage_daily: 0.12,
      usage_total: 2.50,
      limit: 10.00,
    };

    vi.spyOn(api, 'getOpenRouterCredits').mockResolvedValue(mockCredits);

    const { result } = renderHook(() => useOpenRouterCredits(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockCredits);
    expect(api.getOpenRouterCredits).toHaveBeenCalledTimes(1);
  });

  it('fetchOpenRouterCredits delegates to api.getOpenRouterCredits', async () => {
    const mockCredits = {
      enabled: false,
      remaining: 0,
      usage_daily: 0,
      usage_total: 0,
    };

    vi.spyOn(api, 'getOpenRouterCredits').mockResolvedValue(mockCredits);

    const data = await fetchOpenRouterCredits();
    expect(data).toEqual(mockCredits);
  });
});
