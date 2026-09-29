import React, { useState, useEffect } from 'react';
import { api, type ChapterStatus } from '../api';

interface InputPanelProps {
  onComplete: (chapterId: string, pages: string[]) => void;
  pollInterval?: number;
}

export const InputPanel: React.FC<InputPanelProps> = ({ onComplete, pollInterval = 2000 }) => {
  const [chapterId, setChapterId] = useState('');
  const [status, setStatus] = useState<ChapterStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const handleDownload = async () => {
    setError(null);
    setStatus(null);
    try {
      await api.startDownload(chapterId);
      setIsPolling(true);
    } catch (err: any) {
      setError(err.message || 'Failed to start download');
    }
  };

  useEffect(() => {
    if (!isPolling) return;

    let timeoutId: number;
    let isMounted = true;

    const poll = async () => {
      try {
        const res = await api.getStatus(chapterId);
        if (!isMounted) return;
        setStatus(res);

        if (res.status === 'completed' && res.pages) {
          setIsPolling(false);
          onComplete(chapterId, res.pages);
        } else if (res.status === 'error') {
          setIsPolling(false);
          setError(res.error || 'Failed to download chapter');
        } else {
          timeoutId = window.setTimeout(poll, pollInterval);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setIsPolling(false);
        setError(err.message || 'Failed to get status');
      }
    };

    poll();

    return () => {
      isMounted = false;
      window.clearTimeout(timeoutId);
    };
  }, [isPolling, chapterId, onComplete, pollInterval]);

  return (
    <div className="input-panel">
      <h2>Read Manga</h2>
      <div>
        <input
          type="text"
          placeholder="MangaDex Chapter ID"
          value={chapterId}
          onChange={(e) => setChapterId(e.target.value)}
          disabled={isPolling}
        />
        <button onClick={handleDownload} disabled={isPolling || !chapterId}>
          {isPolling ? 'Downloading...' : 'Download'}
        </button>
      </div>
      
      {error && <div className="error" style={{ color: 'red' }}>{error}</div>}
      
      {status && (
        <div className="status">
          Status: {status.status}
          {status.status === 'downloading' && status.progress !== undefined && status.total !== undefined && (
            <span> ({status.progress}/{status.total})</span>
          )}
        </div>
      )}
    </div>
  );
};
