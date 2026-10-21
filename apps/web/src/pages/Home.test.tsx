import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Home } from './Home';

const queryClient = new QueryClient();

describe('Home page', () => {
  it('renders Scrapper button alongside Baixar Novo', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Home />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByRole('button', { name: /scrapper/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /baixar novo/i })).toBeInTheDocument();
  });

  it('opens ScraperModal when Scrapper button is clicked', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Home />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.queryByPlaceholderText(/Cole a URL da obra/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /scrapper/i }));

    expect(screen.getByPlaceholderText(/Cole a URL da obra/i)).toBeInTheDocument();
  });
});

