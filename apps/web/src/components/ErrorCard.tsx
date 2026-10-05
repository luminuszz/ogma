export const ErrorCard = ({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <div className="mt-10 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-center max-w-md">
    <p className="font-semibold mb-2">Erro</p>
    <p className="text-sm">{error}</p>
    <button
      onClick={onRetry}
      className="mt-4 px-4 py-2 bg-panel-light hover:bg-panel rounded-lg text-foreground transition-colors"
    >
      Tentar novamente
    </button>
  </div>
);
