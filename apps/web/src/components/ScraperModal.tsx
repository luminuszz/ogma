import React, { useState } from 'react';
import { Modal } from './Modal';
import { api, type ScraperPreviewResponse } from '../api';
import { Loader2, Globe, CheckSquare, Square } from 'lucide-react';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';

interface ScraperModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ScraperModal({ isOpen, onClose }: ScraperModalProps) {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [preview, setPreview] = useState<ScraperPreviewResponse | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());
  const [isStarting, setIsStarting] = useState(false);
  const queryClient = useQueryClient();

  const handleFetchPreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsLoading(true);
    setPreview(null);
    try {
      const data = await api.previewScraper(url.trim());
      setPreview(data);
      setSelectedChapters(new Set(data.chapters.map(c => c.id)));
    } catch (err: any) {
      toast.error(err.message || 'Erro ao buscar obra.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSelectAll = () => {
    if (!preview) return;
    if (selectedChapters.size === preview.chapters.length) {
      setSelectedChapters(new Set());
    } else {
      setSelectedChapters(new Set(preview.chapters.map(c => c.id)));
    }
  };

  const handleToggleChapter = (id: string) => {
    const next = new Set(selectedChapters);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedChapters(next);
  };

  const handleStartScraping = async () => {
    if (!preview || selectedChapters.size === 0) return;
    setIsStarting(true);
    try {
      const chaptersToScrape = preview.chapters.filter(c => selectedChapters.has(c.id));
      await api.startScraper({
        provider: preview.provider,
        mangaId: preview.mangaId,
        title: preview.title,
        chapters: chaptersToScrape
      });
      toast.success(`${chaptersToScrape.length} capítulos enfileirados para scraping!`);
      queryClient.invalidateQueries({ queryKey: ['library'] });
      onClose();
      setUrl('');
      setPreview(null);
    } catch (err: any) {
      toast.error(err.message || 'Erro ao iniciar scraping.');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Web Scraper de Mangás">
      <div className="flex flex-col gap-4">
        <form onSubmit={handleFetchPreview} className="flex gap-2">
          <input
            type="text"
            placeholder="Cole a URL da obra (ex: LycanToons)..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading || isStarting}
            className="flex-1 bg-panel border border-panel-light rounded-lg px-4 py-2.5 text-foreground focus:outline-none focus:border-primary text-sm"
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="bg-primary hover:bg-primary/90 text-white font-medium px-4 py-2.5 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 text-sm shrink-0"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Globe size={16} />}
            Buscar
          </button>
        </form>

        {preview && (
          <div className="flex flex-col gap-4 mt-2">
            <div className="flex gap-4 items-center p-3 bg-panel/30 border border-panel-light rounded-xl">
              {preview.coverUrl && (
                <img src={preview.coverUrl} alt={preview.title} className="w-16 h-24 object-cover rounded-md shrink-0" />
              )}
              <div className="flex flex-col">
                <h4 className="font-bold text-foreground text-lg">{preview.title}</h4>
                <span className="text-xs text-foreground-muted uppercase tracking-wider">
                  Provedor: {preview.provider} • {preview.chapters.length} capítulos encontrados
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center px-1">
              <span className="text-sm text-foreground-muted">
                {selectedChapters.size} de {preview.chapters.length} selecionados
              </span>
              <button
                type="button"
                onClick={handleToggleSelectAll}
                className="text-sm text-primary hover:underline flex items-center gap-1"
              >
                {selectedChapters.size === preview.chapters.length ? (
                  <>
                    <CheckSquare size={16} /> Desmarcar todos
                  </>
                ) : (
                  <>
                    <Square size={16} /> Marcar todos
                  </>
                )}
              </button>
            </div>

            <div className="max-h-60 overflow-y-auto flex flex-col gap-1 border border-panel-light rounded-lg p-2 bg-panel/10">
              {preview.chapters.map((ch) => {
                const isSelected = selectedChapters.has(ch.id);
                return (
                  <div
                    key={ch.id}
                    onClick={() => handleToggleChapter(ch.id)}
                    className="flex items-center gap-3 p-2 hover:bg-panel/40 rounded cursor-pointer transition-colors"
                  >
                    {isSelected ? <CheckSquare size={16} className="text-primary" /> : <Square size={16} className="text-foreground-muted" />}
                    <span className="text-sm font-medium">{ch.title || `Capítulo ${ch.number}`}</span>
                  </div>
                );
              })}
            </div>

            <button
              type="button"
              onClick={handleStartScraping}
              disabled={isStarting || selectedChapters.size === 0}
              className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-md mt-2"
            >
              {isStarting ? <Loader2 size={18} className="animate-spin" /> : null}
              Iniciar Scraping ({selectedChapters.size} capítulos)
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
