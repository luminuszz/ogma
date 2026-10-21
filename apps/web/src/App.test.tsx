import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

describe('App', () => {
  it('renders home page initially', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );

    expect(screen.getByText('Ogma')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/buscar mangá na sua biblioteca/i)).toBeInTheDocument();
  });
});
