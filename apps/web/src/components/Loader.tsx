import { Loader2 } from 'lucide-react';

export const Loader = ({ message }: { message?: string }) => (
  <div className="flex flex-col items-center justify-center p-8 gap-4 text-foreground-muted">
    <Loader2 size={30} className="animate-spin text-primary" />
    {message && <span className="text-sm">{message}</span>}
  </div>
);
