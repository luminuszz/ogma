import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MangaAccordion } from './MangaAccordion';

describe('MangaAccordion', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderAccordion = (props: React.ComponentProps<typeof MangaAccordion>) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <MangaAccordion {...props} />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('renders title and chapter count with singular label', () => {
    renderAccordion({
      mangaTitle: 'Solo Leveling',
      chapters: [
        { id: '1', chapter: '1', downloaded: 20, total: 20, status: 'done' },
      ],
    });

    expect(screen.getByText('Solo Leveling')).toBeInTheDocument();
    expect(screen.getByText('1 capítulo')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders plural label for multiple chapters', () => {
    renderAccordion({
      mangaTitle: 'One Piece',
      chapters: [
        { id: '1', chapter: '1000', downloaded: 20, total: 20, status: 'done' },
        { id: '2', chapter: '1001', downloaded: 20, total: 20, status: 'done' },
      ],
    });

    expect(screen.getByText('2 capítulos')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders processing badge when at least one chapter has status processing', () => {
    renderAccordion({
      mangaTitle: 'Chainsaw Man',
      chapters: [
        { id: '1', chapter: '1', downloaded: 20, total: 20, status: 'done' },
        { id: '2', chapter: '2', downloaded: 5, total: 20, status: 'processing' },
      ],
    });

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Processando...');
    expect(badge).toHaveClass('animate-pulse');
  });

  it('does not render processing badge when no chapters are processing', () => {
    renderAccordion({
      mangaTitle: 'Jujutsu Kaisen',
      chapters: [
        { id: '1', chapter: '1', downloaded: 20, total: 20, status: 'done' },
        { id: '2', chapter: '2', downloaded: 0, total: 20, status: 'error' },
        { id: '3', chapter: '3', downloaded: 0, total: 20, status: 'pending' },
      ],
    });

    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('renders chapters inside the accordion', () => {
    renderAccordion({
      mangaTitle: 'Tower of God',
      chapters: [
        { id: '1', chapter: '50', downloaded: 25, total: 25, status: 'done' },
        { id: '2', chapter: '51', downloaded: 10, total: 30, status: 'processing' },
      ],
    });

    expect(screen.getByText('Ch. 50')).toBeInTheDocument();
    expect(screen.getByText('Ch. 51')).toBeInTheDocument();
    expect(screen.getByText('Traduzindo... 33% (10/30)')).toBeInTheDocument();
  });

  it('toggles collapse on header click', () => {
    renderAccordion({
      mangaTitle: 'Berserk',
      chapters: [
        { id: '1', chapter: '1', downloaded: 30, total: 30, status: 'done' },
      ],
    });

    const headerButton = screen.getByRole('button', { name: /Berserk/i });
    expect(headerButton).toBeInTheDocument();

    // Toggle close
    fireEvent.click(headerButton);
    // Toggle open again
    fireEvent.click(headerButton);
  });
});
