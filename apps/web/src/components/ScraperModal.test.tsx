import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ScraperModal } from './ScraperModal';
import { api } from '../api';
import toast from 'react-hot-toast';

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ScraperModal', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.restoreAllMocks();
  });

  it('renders input for url when open', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    expect(screen.getByPlaceholderText(/Cole a URL da obra/i)).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={false} onClose={() => {}} />
      </QueryClientProvider>
    );

    expect(screen.queryByPlaceholderText(/Cole a URL da obra/i)).not.toBeInTheDocument();
  });

  it('fetches and displays preview with selectable chapters', async () => {
    const mockPreview = {
      supported: true,
      provider: 'lycantoons',
      mangaId: 'lycantoons:test-manga',
      title: 'Solo Leveling Test',
      coverUrl: 'https://example.com/cover.jpg',
      chapters: [
        { id: 'ch-1', number: '1', title: 'Capítulo 1', url: 'https://example.com/ch-1' },
        { id: 'ch-2', number: '2', title: 'Capítulo 2', url: 'https://example.com/ch-2' },
      ],
    };

    vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreview);

    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
    fireEvent.change(input, { target: { value: 'https://lycantoons.com/series/test' } });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(screen.getByText('Solo Leveling Test')).toBeInTheDocument();
    });

    expect(screen.getByText(/2 de 2 selecionados/i)).toBeInTheDocument();
    expect(screen.getByText('Capítulo 1')).toBeInTheDocument();
    expect(screen.getByText('Capítulo 2')).toBeInTheDocument();
  });

  it('allows toggling chapters and starting scraper', async () => {
    const onClose = vi.fn();
    const mockPreview = {
      supported: true,
      provider: 'lycantoons',
      mangaId: 'lycantoons:test-manga',
      title: 'Solo Leveling Test',
      coverUrl: 'https://example.com/cover.jpg',
      chapters: [
        { id: 'ch-1', number: '1', title: 'Capítulo 1', url: 'https://example.com/ch-1' },
        { id: 'ch-2', number: '2', title: 'Capítulo 2', url: 'https://example.com/ch-2' },
      ],
    };

    vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreview);
    vi.spyOn(api, 'startScraper').mockResolvedValue({ status: 'queued', count: 1 });

    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={onClose} />
      </QueryClientProvider>
    );

    fireEvent.change(screen.getByPlaceholderText(/Cole a URL da obra/i), {
      target: { value: 'https://lycantoons.com/series/test' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(screen.getByText('Solo Leveling Test')).toBeInTheDocument();
    });

    // Unselect first chapter
    fireEvent.click(screen.getByText('Capítulo 1'));
    expect(screen.getByText(/1 de 2 selecionados/i)).toBeInTheDocument();

    // Start scraping
    const startButton = screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(api.startScraper).toHaveBeenCalledWith({
        provider: 'lycantoons',
        mangaId: 'lycantoons:test-manga',
        title: 'Solo Leveling Test',
        chapters: [mockPreview.chapters[1]],
      });
      expect(toast.success).toHaveBeenCalledWith('1 capítulos enfileirados para scraping!');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('shows error toast if preview fails', async () => {
    vi.spyOn(api, 'previewScraper').mockRejectedValue(new Error('URL não suportada'));

    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    fireEvent.change(screen.getByPlaceholderText(/Cole a URL da obra/i), {
      target: { value: 'https://unsupported.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('URL não suportada');
    });
  });

  it('handles toggle select all button', async () => {
    const mockPreview = {
      supported: true,
      provider: 'lycantoons',
      mangaId: 'lycantoons:test-manga',
      title: 'Solo Leveling Test',
      chapters: [
        { id: 'ch-1', number: '1', title: 'Capítulo 1', url: 'https://example.com/ch-1' },
        { id: 'ch-2', number: '2', title: 'Capítulo 2', url: 'https://example.com/ch-2' },
      ],
    };

    vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreview);

    render(
      <QueryClientProvider client={queryClient}>
        <ScraperModal isOpen={true} onClose={() => {}} />
      </QueryClientProvider>
    );

    fireEvent.change(screen.getByPlaceholderText(/Cole a URL da obra/i), {
      target: { value: 'https://lycantoons.com/series/test' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

    await waitFor(() => {
      expect(screen.getByText('Solo Leveling Test')).toBeInTheDocument();
    });

    // Deselect all
    const deselectButton = screen.getByRole('button', { name: /Desmarcar todos/i });
    fireEvent.click(deselectButton);
    expect(screen.getByText(/0 de 2 selecionados/i)).toBeInTheDocument();

    // Select all
    const selectAllButton = screen.getByRole('button', { name: /Marcar todos/i });
    fireEvent.click(selectAllButton);
    expect(screen.getByText(/2 de 2 selecionados/i)).toBeInTheDocument();
  });
});
