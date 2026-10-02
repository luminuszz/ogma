import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ReaderComponent } from './ReaderComponent';

describe('ReaderComponent', () => {
  it('renders images for each page', () => {
    const chapterId = 'test-chapter';
    const pages = ['1.png', '2.png', '3.png'];
    
    render(<ReaderComponent chapterId={chapterId} pages={pages} />);

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(3);
    
    expect(images[0]).toHaveAttribute('src', '/data/test-chapter/1.png');
    expect(images[1]).toHaveAttribute('src', '/data/test-chapter/2.png');
    expect(images[2]).toHaveAttribute('src', '/data/test-chapter/3.png');
  });

  it('shows empty message when no pages', () => {
    render(<ReaderComponent chapterId="test-chapter" pages={[]} />);
    expect(screen.getByText(/No pages to display/i)).toBeInTheDocument();
  });
});
