import { Loader2 } from 'lucide-react';
import { ProgressBar } from '@/components/ProgressBar';

interface LoadingStatusProps {
  completed: number;
  total: number;
}

export const LoadingStatus = ({ completed, total }: LoadingStatusProps) => {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const remaining = total - completed;

  return (
    <div className="mt-20 flex flex-col items-center gap-6 text-foreground-muted px-4 w-full max-w-sm mx-auto">
      <Loader2 size={40} className="animate-spin text-primary" />
      <div className="w-full space-y-2">
        <div className="flex justify-between text-sm">
          <span>Traduzindo páginas...</span>
          <span className="text-primary font-semibold">{completed} / {total}</span>
        </div>
        <ProgressBar percent={percent} />
        <p className="text-xs text-center text-foreground-muted">
          {remaining} página{remaining !== 1 ? 's' : ''} restante{remaining !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};
