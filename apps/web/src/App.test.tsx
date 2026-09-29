import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';
import { api } from './api';

vi.mock('./api', () => ({
  api: {
    startDownload: vi.fn(),
    getStatus: vi.fn(),
  },
}));

describe('App', () => {
  it('renders InputPanel initially and switches to Reader on completion', async () => {
    vi.mocked(api.startDownload).mockResolvedValue();
    vi.mocked(api.getStatus).mockResolvedValue({ 
      status: 'completed', 
      pages: ['p1.png', 'p2.png'] 
    });

    render(<App />);
    
    expect(screen.getByText(/Ogma Web Reader/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/MangaDex Chapter ID/i)).toBeInTheDocument();

    // Trigger download
    const input = screen.getByPlaceholderText(/MangaDex Chapter ID/i);
    fireEvent.change(input, { target: { value: 'chapter-123' } });
    
    const button = screen.getByRole('button', { name: /Download/i });
    fireEvent.click(button);

    // Should switch to reader
    await waitFor(() => {
      expect(screen.getByText(/← Back to Download/i)).toBeInTheDocument();
    });

    // Check images rendered
    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute('src', '/data/chapter-123/p1.png');

    // Go back
    fireEvent.click(screen.getByText(/← Back to Download/i));
    expect(screen.getByPlaceholderText(/MangaDex Chapter ID/i)).toBeInTheDocument();
  });
});
