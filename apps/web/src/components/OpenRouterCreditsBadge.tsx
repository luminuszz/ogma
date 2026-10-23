import React from 'react';
import { Coins, RefreshCw } from 'lucide-react';
import { useOpenRouterCredits } from '../hooks/useOpenRouterCredits';

const formatUSD = (val: number | undefined | null): string => {
  const num = typeof val === 'number' && !isNaN(val) ? val : 0;
  return num.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getCreditsStatusClasses = (remaining: number): string => {
  if (remaining >= 2.0) {
    return 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10';
  }
  if (remaining >= 0.5) {
    return 'border-amber-500/30 text-amber-400 bg-amber-500/10';
  }
  return 'border-rose-500/30 text-rose-400 bg-rose-500/10';
};

export const OpenRouterCreditsBadge: React.FC = () => {
  const { data, isFetching, refetch } = useOpenRouterCredits();

  if (!data || !data.enabled) {
    return null;
  }

  const formattedRemaining = formatUSD(data.remaining);
  const statusClasses = getCreditsStatusClasses(data.remaining);

  const handleRefresh = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    refetch();
  };

  return (
    <div
      className="relative group inline-flex items-center"
      role="status"
      aria-label={`Saldo OpenRouter: ${formattedRemaining}`}
    >
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium transition-colors ${statusClasses}`}
        title={`Saldo OpenRouter: ${formattedRemaining}`}
      >
        <Coins size={16} className="shrink-0" aria-hidden="true" />
        <span className="font-semibold tabular-nums">{formattedRemaining}</span>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={isFetching}
          className="p-1 -mr-1 rounded-full hover:bg-white/10 active:scale-95 transition-all text-current opacity-70 hover:opacity-100 disabled:opacity-40"
          aria-label="Atualizar saldo"
          title="Atualizar saldo"
        >
          <RefreshCw
            size={13}
            className={`transition-transform ${isFetching ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      {/* Tooltip */}
      <div
        role="tooltip"
        className="absolute top-full mt-2 left-1/2 -translate-x-1/2 flex flex-col gap-1 px-3 py-2 rounded-xl bg-panel border border-panel-light text-foreground text-xs shadow-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap min-w-max"
      >
        <span className="font-medium">
          Gasto hoje: {formatUSD(data.usage_daily)}
        </span>
        <span className="font-medium">
          Gasto total: {formatUSD(data.usage_total)}
        </span>
        {data.limit != null && (
          <span className="font-medium">
            Limite: {formatUSD(data.limit)}
          </span>
        )}
      </div>
    </div>
  );
};
