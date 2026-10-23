import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OpenRouterCreditsBadge } from './OpenRouterCreditsBadge';
import * as useOpenRouterCreditsModule from '../hooks/useOpenRouterCredits';

vi.mock('../hooks/useOpenRouterCredits', () => ({
  useOpenRouterCredits: vi.fn(),
}));

describe('OpenRouterCreditsBadge', () => {
  const mockRefetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when data is undefined or null', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    const { container } = render(<OpenRouterCreditsBadge />);
    expect(container.firstChild).toBeNull();
  });

  it('does not render when enabled is false', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: false,
        remaining: 10.0,
        usage_daily: 0,
        usage_total: 0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    const { container } = render(<OpenRouterCreditsBadge />);
    expect(container.firstChild).toBeNull();
  });

  it('renders green status badge when remaining >= 2.00', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 2.0,
        usage_daily: 0.1,
        usage_total: 1.5,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(screen.getByText('$2.00')).toBeInTheDocument();

    const pill = badge.querySelector('div');
    expect(pill).toHaveClass('border-emerald-500/30');
    expect(pill).toHaveClass('text-emerald-400');
    expect(pill).toHaveClass('bg-emerald-500/10');
  });

  it('renders yellow status badge when remaining is between 0.50 and 1.99', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 1.29,
        usage_daily: 0.25,
        usage_total: 3.4,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(screen.getByText('$1.29')).toBeInTheDocument();

    const pill = badge.querySelector('div');
    expect(pill).toHaveClass('border-amber-500/30');
    expect(pill).toHaveClass('text-amber-400');
    expect(pill).toHaveClass('bg-amber-500/10');
  });

  it('renders yellow status badge exactly at boundary 0.50', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 0.5,
        usage_daily: 0.1,
        usage_total: 2.0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const badge = screen.getByRole('status');
    expect(screen.getByText('$0.50')).toBeInTheDocument();

    const pill = badge.querySelector('div');
    expect(pill).toHaveClass('border-amber-500/30');
    expect(pill).toHaveClass('text-amber-400');
    expect(pill).toHaveClass('bg-amber-500/10');
  });

  it('renders red status badge when remaining < 0.50', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 0.49,
        usage_daily: 0.5,
        usage_total: 5.0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const badge = screen.getByRole('status');
    expect(screen.getByText('$0.49')).toBeInTheDocument();

    const pill = badge.querySelector('div');
    expect(pill).toHaveClass('border-rose-500/30');
    expect(pill).toHaveClass('text-rose-400');
    expect(pill).toHaveClass('bg-rose-500/10');
  });

  it('renders red status badge when remaining is 0', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 0,
        usage_daily: 0,
        usage_total: 10.0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const badge = screen.getByRole('status');
    expect(screen.getByText('$0.00')).toBeInTheDocument();

    const pill = badge.querySelector('div');
    expect(pill).toHaveClass('border-rose-500/30');
    expect(pill).toHaveClass('text-rose-400');
    expect(pill).toHaveClass('bg-rose-500/10');
  });

  it('displays tooltip with daily spend, total spend and limit when limit is present', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 4.5,
        usage_daily: 0.35,
        usage_total: 12.8,
        limit: 20.0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    expect(screen.getByText(/Gasto hoje:\s*\$0\.35/i)).toBeInTheDocument();
    expect(screen.getByText(/Gasto total:\s*\$12\.80/i)).toBeInTheDocument();
    expect(screen.getByText(/Limite:\s*\$20\.00/i)).toBeInTheDocument();
  });

  it('displays tooltip without limit when limit is null or undefined', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 4.5,
        usage_daily: 0.35,
        usage_total: 12.8,
        limit: null,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    expect(screen.getByText(/Gasto hoje:\s*\$0\.35/i)).toBeInTheDocument();
    expect(screen.getByText(/Gasto total:\s*\$12\.80/i)).toBeInTheDocument();
    expect(screen.queryByText(/Limite:/i)).not.toBeInTheDocument();
  });

  it('calls refetch when refresh button is clicked', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 3.0,
        usage_daily: 0.1,
        usage_total: 1.0,
      },
      isLoading: false,
      isFetching: false,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const refreshButton = screen.getByRole('button', { name: /atualizar saldo/i });
    expect(refreshButton).toBeInTheDocument();

    fireEvent.click(refreshButton);
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('animates spin on refresh icon and disables button when isFetching is true', () => {
    vi.mocked(useOpenRouterCreditsModule.useOpenRouterCredits).mockReturnValue({
      data: {
        enabled: true,
        remaining: 3.0,
        usage_daily: 0.1,
        usage_total: 1.0,
      },
      isLoading: false,
      isFetching: true,
      refetch: mockRefetch,
    } as any);

    render(<OpenRouterCreditsBadge />);

    const refreshButton = screen.getByRole('button', { name: /atualizar saldo/i });
    expect(refreshButton).toBeDisabled();

    const icon = refreshButton.querySelector('svg');
    expect(icon).toHaveClass('animate-spin');
  });
});
