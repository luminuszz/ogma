export const ProgressBar = ({ percent }: { percent: number }) => (
  <div className="w-full bg-panel-light rounded-full h-2">
    <div
      className="bg-primary h-2 rounded-full transition-all duration-500"
      style={{ width: `${percent}%` }}
    />
  </div>
);
