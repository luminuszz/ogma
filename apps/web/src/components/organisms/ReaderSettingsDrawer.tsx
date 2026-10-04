import { X } from 'lucide-react';
import { useReadSettings } from '@/hooks/useReadSettings';

interface ReaderSettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ReaderSettingsDrawer = ({ isOpen, onClose }: ReaderSettingsDrawerProps) => {
  const { readingDirection, imageFit, loadingMode, update } = useReadSettings();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      <div className="relative w-80 bg-panel h-full border-l border-panel-light flex flex-col shadow-2xl animate-fade-in-right">
        <div className="p-4 flex items-center justify-between border-b border-panel-light">
          <h3 className="font-semibold text-lg">Settings</h3>
          <button
            onClick={onClose}
            className="p-2 text-foreground-muted hover:text-foreground rounded-lg hover:bg-panel-light transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 flex-1 overflow-y-auto space-y-8">
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Reading Direction</h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => update("direction", "webtoon")}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${readingDirection === 'webtoon' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Webtoon
              </button>
              <button
                onClick={() => update("direction", 'paged')}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${readingDirection === 'paged' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Paged (LTR)
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Image Fit</h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => update("fit",'width')}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${imageFit === 'width' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Width
              </button>
              <button
                onClick={() => update("fit", 'height')}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${imageFit === 'height' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Height
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="text-sm font-medium text-foreground-muted uppercase tracking-wider">Loading Mode</h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => update("loading",'real-time')}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${loadingMode === 'real-time' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Real-time
              </button>
              <button
                onClick={() => update("loading",'wait')}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${loadingMode === 'wait' ? 'bg-primary/20 border border-primary text-primary' : 'bg-base border border-panel-light text-foreground-muted hover:text-foreground'}`}
              >
                Wait all
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
