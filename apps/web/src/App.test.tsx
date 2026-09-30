import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders home page initially', () => {
    render(<App />);

    expect(screen.getByText('Ogma')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. 5e1a3b11/i)).toBeInTheDocument();
  });
});
