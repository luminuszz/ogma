import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LibraryCard } from './LibraryCard';
import { api } from '../api';

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('LibraryCard', () => {
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

  const renderCard = (props: React.ComponentProps<typeof LibraryCard>) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LibraryCard {...props} />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe('Processing state', () => {
    it('renders progress text and visual progress bar when processing', () => {
      renderCard({
        id: 'chap-1',
        chapter: '10',
        downloaded: 5,
        total: 10,
        status: 'processing',
      });

      expect(screen.getByText('Ch. 10')).toBeInTheDocument();
      expect(screen.getByText('Traduzindo... 50% (5/10)')).toBeInTheDocument();

      const progressBar = screen.getByRole('progressbar', { name: /Progresso da tradução/i });
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');

      const innerBar = progressBar.firstElementChild;
      expect(innerBar).toHaveStyle({ width: '50%' });
    });

    it('renders indeterminate state with 0% bar when total is 0', () => {
      renderCard({
        id: 'chap-1',
        chapter: '1',
        downloaded: 0,
        total: 0,
        status: 'processing',
      });

      expect(screen.getByText('Traduzindo... Iniciando')).toBeInTheDocument();
      const progressBar = screen.getByRole('progressbar', { name: /Progresso da tradução/i });
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
      expect(progressBar.firstElementChild).toHaveStyle({ width: '0%' });
    });
  });

  describe('Error state', () => {
    it('shows paused page details and "Retomar" retry button when downloaded > 0', async () => {
      const retrySpy = vi.spyOn(api, 'retryChapter').mockResolvedValue(undefined);

      renderCard({
        id: 'chap-2',
        chapter: '12',
        downloaded: 5,
        total: 20,
        status: 'error',
      });

      expect(screen.getByText('Pausado na pág. 6/20 • 15 restantes')).toBeInTheDocument();

      const resumeButton = screen.getByRole('button', { name: /Retomar \(15 restam\)/i });
      expect(resumeButton).toBeInTheDocument();

      fireEvent.click(resumeButton);

      await waitFor(() => {
        expect(retrySpy).toHaveBeenCalledWith('chap-2', expect.anything());
      });
    });

    it('shows generic error and "Tentar Novamente" retry button when downloaded is 0', async () => {
      const retrySpy = vi.spyOn(api, 'retryChapter').mockResolvedValue(undefined);

      renderCard({
        id: 'chap-3',
        chapter: '5',
        downloaded: 0,
        total: 25,
        status: 'error',
      });

      expect(screen.getByText('Erro na tradução (0/25)')).toBeInTheDocument();

      const retryButton = screen.getByRole('button', { name: /Tentar Novamente/i });
      expect(retryButton).toBeInTheDocument();

      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(retrySpy).toHaveBeenCalledWith('chap-3', expect.anything());
      });
    });
  });

  describe('Pending state', () => {
    it('renders queued indicator when status is pending', () => {
      renderCard({
        id: 'chap-4',
        chapter: '7',
        downloaded: 0,
        total: 15,
        status: 'pending',
      });

      expect(screen.getByText('Na fila de espera')).toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  describe('Completed state', () => {
    it('renders translated page count when completed', () => {
      renderCard({
        id: 'chap-5',
        chapter: '8',
        downloaded: 20,
        total: 20,
        status: 'done',
      });

      expect(screen.getByText('Traduzido: 20/20 páginas • PT-BR')).toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  describe('Card actions', () => {
    it('confirms and triggers delete mutation', async () => {
      const deleteSpy = vi.spyOn(api, 'deleteChapter').mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      renderCard({
        id: 'chap-6',
        chapter: '1',
        downloaded: 10,
        total: 10,
        status: 'done',
      });

      const deleteButton = screen.getByTitle('Deletar Capítulo');
      fireEvent.click(deleteButton);

      expect(confirmSpy).toHaveBeenCalled();
      await waitFor(() => {
        expect(deleteSpy).toHaveBeenCalledWith('chap-6', expect.anything());
      });
    });

    it('renders link to reader', () => {
      renderCard({
        id: 'chap-reader-1',
        chapter: '1',
        downloaded: 10,
        total: 10,
        status: 'done',
      });

      const readerLink = screen.getByRole('link', { name: /Ler/i });
      expect(readerLink).toHaveAttribute('href', '/reader/chap-reader-1');
    });
  });
});
