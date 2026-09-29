import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { InputPanel } from './InputPanel';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    startDownload: vi.fn(),
    getStatus: vi.fn(),
  },
}));

describe('InputPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits chapter ID and polls for status', async () => {
    vi.mocked(api.startDownload).mockResolvedValue();
    vi.mocked(api.getStatus)
      .mockResolvedValueOnce({ status: 'queued' })
      .mockResolvedValue({ status: 'completed', pages: ['1.png', '2.png'] });

    const onComplete = vi.fn();
    render(<InputPanel onComplete={onComplete} pollInterval={1} />);

    // Enter Chapter ID
    const input = screen.getByPlaceholderText(/MangaDex Chapter ID/i);
    fireEvent.change(input, { target: { value: 'test-chapter-123' } });

    // Submit
    const button = screen.getByRole('button', { name: /Download/i });
    fireEvent.click(button);

    // Should call startDownload
    expect(api.startDownload).toHaveBeenCalledWith('test-chapter-123');

    // Wait for queued status to be processed
    await waitFor(() => {
      expect(screen.getByText(/Status: queued/i)).toBeInTheDocument();
    });

    // Check completion
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('test-chapter-123', ['1.png', '2.png']);
    });
  });

  it('shows error message on failure', async () => {
    vi.mocked(api.startDownload).mockRejectedValue(new Error('Network Error'));

    render(<InputPanel onComplete={vi.fn()} />);

    const input = screen.getByPlaceholderText(/MangaDex Chapter ID/i);
    fireEvent.change(input, { target: { value: 'test-error-chapter' } });

    const button = screen.getByRole('button', { name: /Download/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Network Error/i)).toBeInTheDocument();
    });
  });
});
