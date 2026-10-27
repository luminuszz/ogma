import React, { useState, useMemo } from 'react';
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
  const [targetMangaId, setTargetMangaId] = useState<string>('');
  const [forceTranslate, setForceTranslate] = useState<boolean>(true);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());
  const [isStarting, setIsStarting] = useState(false);
  const queryClient = useQueryClient();

  const selectedExistingManga = useMemo(
    () => preview?.existingWorks?.find((w) => w.id === targetMangaId),
    [preview, targetMangaId]
  );

  const existingNumbers = useMemo(
    () => new Set(selectedExistingManga?.existingChapterNumbers || []),
    [selectedExistingManga]
  );

  const suggestedWork = useMemo(
    () => (preview?.suggestedMangaId ? preview.existingWorks?.find((w) => w.id === preview.suggestedMangaId) : null),
    [preview]
  );

  const handleFetchPreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsLoading(true);
    setPreview(null);
    try {
      const data = await api.previewScraper(url.trim());
      setPreview(data);

      const initialTargetId = data.suggestedMangaId || data.mangaId;
      setTargetMangaId(initialTargetId);

      const targetWork = data.existingWorks?.find((w) => w.id === initialTargetId);
      const existing = new Set(targetWork?.existingChapterNumbers || []);
      const missingChapters = data.chapters.filter((c) => !existing.has(c.number));
      setSelectedChapters(new Set(missingChapters.map((c) => c.id)));
    } catch (err: any) {
      toast.error(err.message || 'Erro ao buscar obra.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTargetChange = (newTargetId: string) => {
    setTargetMangaId(newTargetId);
    if (!preview) return;
    const work = preview.existingWorks?.find((w) => w.id === newTargetId);
    const existing = new Set(work?.existingChapterNumbers || []);
    setSelectedChapters(new Set(preview.chapters.filter((c) => !existing.has(c.number)).map((c) => c.id)));
  };

  const handleSelectMissing = () => {
    if (!preview) return;
    const missing = preview.chapters.filter((c) => !existingNumbers.has(c.number)).map((c) => c.id);
    setSelectedChapters(new Set(missing));
  };

  const handleToggleSelectAll = () => {
    if (!preview) return;
    if (selectedChapters.size === preview.chapters.length) {
      setSelectedChapters(new Set());
    } else {
      setSelectedChapters(new Set(preview.chapters.map((c) => c.id)));
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
      const chaptersToScrape = preview.chapters.filter((c) => selectedChapters.has(c.id));
      await api.startScraper({
        provider: preview.provider,
        mangaId: targetMangaId || preview.mangaId,
        title: preview.title,
        chapters: chaptersToScrape,
        forceTranslate,
      });
      toast.success(`${chaptersToScrape.length} capítulos enfileirados para scraping!`);
      queryClient.invalidateQueries({ queryKey: ['library'] });
      onClose();
      setUrl('');
      setPreview(null);
      setTargetMangaId('');
      setForceTranslate(true);
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
            placeholder="Cole a URL da obra (ex: LycanToons, Valir Scans, MangáDash)..."
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

            {/* Target Manga Linking Selection */}
            <div className="flex flex-col gap-2 p-3 bg-panel/30 border border-panel-light rounded-xl">
              <span className="text-xs font-semibold text-foreground-muted uppercase tracking-wider">
                Destino da Obra na Biblioteca
              </span>
              <div className="flex flex-col gap-2 text-sm">
                {suggestedWork && (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="targetManga"
                      value={suggestedWork.id}
                      checked={targetMangaId === suggestedWork.id}
                      onChange={() => handleTargetChange(suggestedWork.id)}
                      className="text-primary focus:ring-primary"
                    />
                    <span className="font-medium text-foreground">
                      Vincular a: {suggestedWork.title}
                    </span>
                  </label>
                )}

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="targetManga"
                    value={preview.mangaId}
                    checked={targetMangaId === preview.mangaId}
                    onChange={() => handleTargetChange(preview.mangaId)}
                    className="text-primary focus:ring-primary"
                  />
                  <span className="font-medium text-foreground">
                    Criar como nova obra ({preview.title})
                  </span>
                </label>

                {preview.existingWorks && preview.existingWorks.length > 0 && (
                  <div className="flex items-center gap-2 mt-1">
                    <label htmlFor="other-manga-select" className="text-xs text-foreground-muted whitespace-nowrap">
                      Ou vincular a outra:
                    </label>
                    <select
                      id="other-manga-select"
                      value={
                        targetMangaId !== preview.mangaId && targetMangaId !== preview.suggestedMangaId
                          ? targetMangaId
                          : ''
                      }
                      onChange={(e) => {
                        if (e.target.value) {
                          handleTargetChange(e.target.value);
                        }
                      }}
                      className="bg-panel border border-panel-light rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:border-primary flex-1"
                    >
                      <option value="">Selecione uma obra...</option>
                      {preview.existingWorks.map((work) => (
                        <option key={work.id} value={work.id}>
                          {work.title} ({work.existingChapterNumbers.length} capítulos baixados)
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-between items-center px-1 flex-wrap gap-2">
              <span className="text-sm text-foreground-muted">
                {selectedChapters.size} de {preview.chapters.length} selecionados
              </span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleSelectMissing}
                  className="text-sm text-primary hover:underline"
                >
                  Selecionar apenas faltantes
                </button>
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
            </div>

            <div className="max-h-60 overflow-y-auto flex flex-col gap-1 border border-panel-light rounded-lg p-2 bg-panel/10">
              {preview.chapters.map((ch) => {
                const isSelected = selectedChapters.has(ch.id);
                const isDownloaded = existingNumbers.has(ch.number);
                return (
                  <div
                    key={ch.id}
                    onClick={() => handleToggleChapter(ch.id)}
                    className="flex items-center justify-between p-2 hover:bg-panel/40 rounded cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {isSelected ? (
                        <CheckSquare size={16} className="text-primary" />
                      ) : (
                        <Square size={16} className="text-foreground-muted" />
                      )}
                      <span className="text-sm font-medium">{ch.title || `Capítulo ${ch.number}`}</span>
                    </div>
                    {isDownloaded ? (
                      <span className="text-[10px] bg-panel-light text-foreground-muted px-1.5 py-0.5 rounded font-semibold shrink-0">
                        Já baixado
                      </span>
                    ) : (
                      <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-semibold shrink-0">
                        Novo
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Translation Toggle */}
            <label className="flex items-center gap-2 p-2 bg-panel/20 border border-panel-light rounded-lg cursor-pointer text-sm text-foreground">
              <input
                type="checkbox"
                checked={forceTranslate}
                onChange={(e) => setForceTranslate(e.target.checked)}
                className="rounded border-panel-light text-primary focus:ring-primary h-4 w-4"
              />
              <span>Traduzir páginas automaticamente (EN ➔ PT-BR) com OCR & IA</span>
            </label>

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
