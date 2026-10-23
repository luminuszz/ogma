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
        forceTranslate: true,
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

  describe('Multi-Provider Linking, Chapter Badges, and Translation', () => {
    const mockPreviewResponse = {
      supported: true,
      provider: 'valirscans',
      mangaId: 'valirscans:the-counts-secret-maid',
      title: "The Count's Secret Maid",
      coverUrl: 'https://valirscans.org/cover.webp',
      chapters: [
        { id: 'valirscans:1', number: '1', title: 'Capítulo 1', url: 'https://valirscans.org/1' },
        { id: 'valirscans:101', number: '101', title: 'Capítulo 101', url: 'https://valirscans.org/101' },
      ],
      existingWorks: [
        {
          id: 'lycantoons:a-empregada-secreta-do-conde',
          title: 'A Empregada Secreta do Conde',
          existingChapterNumbers: ['1'],
        },
      ],
      suggestedMangaId: 'lycantoons:a-empregada-secreta-do-conde',
    };

    it('suggests linking to existing manga and marks chapter 1 as Já baixado and 101 as Novo', async () => {
      vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreviewResponse);

      render(
        <QueryClientProvider client={queryClient}>
          <ScraperModal isOpen={true} onClose={() => {}} />
        </QueryClientProvider>
      );

      const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
      fireEvent.change(input, {
        target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

      await waitFor(() => {
        expect(screen.getByText("The Count's Secret Maid")).toBeInTheDocument();
      });

      // Verify suggested linking is displayed and active
      expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();

      // Verify badges
      expect(screen.getByText('Já baixado')).toBeInTheDocument();
      expect(screen.getByText('Novo')).toBeInTheDocument();

      // Verify chapter 101 is selected by default, and chapter 1 is unselected
      const startBtn = screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i });
      expect(startBtn).toBeInTheDocument();
    });

    it('submits target manga id and forceTranslate on start scraping', async () => {
      vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreviewResponse);
      vi.spyOn(api, 'startScraper').mockResolvedValue({ status: 'queued', count: 1 });

      render(
        <QueryClientProvider client={queryClient}>
          <ScraperModal isOpen={true} onClose={() => {}} />
        </QueryClientProvider>
      );

      const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
      fireEvent.change(input, {
        target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

      await waitFor(() => {
        expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i }));

      await waitFor(() => {
        expect(api.startScraper).toHaveBeenCalledWith(
          expect.objectContaining({
            mangaId: 'lycantoons:a-empregada-secreta-do-conde',
            forceTranslate: true,
            chapters: [expect.objectContaining({ id: 'valirscans:101' })],
          })
        );
      });
    });

    it('allows resetting selection with "Selecionar apenas faltantes"', async () => {
      vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreviewResponse);

      render(
        <QueryClientProvider client={queryClient}>
          <ScraperModal isOpen={true} onClose={() => {}} />
        </QueryClientProvider>
      );

      const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
      fireEvent.change(input, {
        target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

      await waitFor(() => {
        expect(screen.getByText("The Count's Secret Maid")).toBeInTheDocument();
      });

      // Mark all
      const selectAllBtn = screen.getByRole('button', { name: /Marcar todos/i });
      fireEvent.click(selectAllBtn);
      expect(screen.getByText(/2 de 2 selecionados/i)).toBeInTheDocument();

      // Click "Selecionar apenas faltantes"
      const selectMissingBtn = screen.getByRole('button', { name: /Selecionar apenas faltantes/i });
      fireEvent.click(selectMissingBtn);
      expect(screen.getByText(/1 de 2 selecionados/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i })).toBeInTheDocument();
    });

    it('toggles forceTranslate off and submits forceTranslate: false', async () => {
      vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreviewResponse);
      vi.spyOn(api, 'startScraper').mockResolvedValue({ status: 'queued', count: 1 });

      render(
        <QueryClientProvider client={queryClient}>
          <ScraperModal isOpen={true} onClose={() => {}} />
        </QueryClientProvider>
      );

      const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
      fireEvent.change(input, {
        target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

      await waitFor(() => {
        expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();
      });

      // Toggle translation checkbox off
      const translateCheckbox = screen.getByLabelText(/Traduzir páginas automaticamente/i);
      expect(translateCheckbox).toBeChecked();
      fireEvent.click(translateCheckbox);
      expect(translateCheckbox).not.toBeChecked();

      fireEvent.click(screen.getByRole('button', { name: /Iniciar Scraping \(1 capítulos\)/i }));

      await waitFor(() => {
        expect(api.startScraper).toHaveBeenCalledWith(
          expect.objectContaining({
            mangaId: 'lycantoons:a-empregada-secreta-do-conde',
            forceTranslate: false,
          })
        );
      });
    });

    it('allows switching target manga to "Criar como nova obra"', async () => {
      vi.spyOn(api, 'previewScraper').mockResolvedValue(mockPreviewResponse);
      vi.spyOn(api, 'startScraper').mockResolvedValue({ status: 'queued', count: 2 });

      render(
        <QueryClientProvider client={queryClient}>
          <ScraperModal isOpen={true} onClose={() => {}} />
        </QueryClientProvider>
      );

      const input = screen.getByPlaceholderText(/Cole a URL da obra/i);
      fireEvent.change(input, {
        target: { value: 'https://valirscans.org/series/comic/the-counts-secret-maid?page=2' },
      });
      fireEvent.click(screen.getByRole('button', { name: /Buscar/i }));

      await waitFor(() => {
        expect(screen.getByText(/Vincular a: A Empregada Secreta do Conde/i)).toBeInTheDocument();
      });

      // Switch target to "Criar como nova obra"
      const newMangaRadio = screen.getByLabelText(/Criar como nova obra/i);
      fireEvent.click(newMangaRadio);

      // Now both chapters should be considered "Novo" since this new work has no chapters yet
      expect(screen.queryByText('Já baixado')).not.toBeInTheDocument();
      expect(screen.getAllByText('Novo')).toHaveLength(2);
      expect(screen.getByText(/2 de 2 selecionados/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /Iniciar Scraping \(2 capítulos\)/i }));

      await waitFor(() => {
        expect(api.startScraper).toHaveBeenCalledWith(
          expect.objectContaining({
            mangaId: 'valirscans:the-counts-secret-maid',
            chapters: expect.arrayContaining([
              expect.objectContaining({ id: 'valirscans:1' }),
              expect.objectContaining({ id: 'valirscans:101' }),
            ]),
          })
        );
      });
    });
  });
});
