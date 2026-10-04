import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, BookMarked, Plus, CheckSquare, Square } from 'lucide-react';
import { useStartDownload, useLibrary, useStartBulkDownload } from '@/hooks/useManga';
import { useQueryClient } from '@tanstack/react-query';

import { MangaAccordion } from '@/components/molecules/MangaAccordion';
import { Loader } from '@/components/atoms/Loader';
import { Modal } from '@/components/atoms/Modal';

export function Home() {
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [inputUrl, setInputUrl] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());

  const navigate = useNavigate();
  const startDownload = useStartDownload();
  const startBulkDownload = useStartBulkDownload();
  const queryClient = useQueryClient();
  const { data: libraryData, isLoading: libraryLoading } = useLibrary();




  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;

    setError(null);
    setIsLoading(true);

    try {
      const uuidMatch = inputUrl.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
      const extractedId = uuidMatch ? uuidMatch[0] : inputUrl.trim();

      if (inputUrl.includes('/title/') || chapters.length > 0) {
        const res = await fetch(`/api/manga/${extractedId}/chapters`);
        if (!res.ok) throw new Error('Failed to fetch chapters');
        const data = await res.json();
        setChapters(data.chapters);
      } else {
        await startDownload.mutateAsync({ chapterId: extractedId, sourceLang });
        setIsSearchModalOpen(false);
        navigate(`/reader/${encodeURIComponent(extractedId)}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to process request');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center p-4 max-w-4xl mx-auto w-full gap-8 mt-10">

      {/* HEADER & ACTIONS */}
      <div className="w-full flex justify-between items-end mb-4">
        <div className="flex items-center gap-2">
          <BookMarked className="text-primary" size={32} />
          <h2 className="text-3xl font-bold text-foreground">Sua Biblioteca</h2>
        </div>

        <button
          onClick={() => setIsSearchModalOpen(true)}
          className="bg-primary hover:bg-primary/90 text-white font-medium py-2 px-6 rounded-full flex items-center justify-center transition-colors shadow-lg"
        >
          <Plus size={18} className="mr-2" />
          Baixar Novo
        </button>
      </div>

      {/* LIBRARY SECTION */}
      <div className="w-full flex flex-col gap-4 mb-20">
        {libraryLoading ? (
          <Loader message="Carregando obras salvas..." />
        ) : libraryData && libraryData.length > 0 ? (
          <div className="flex flex-col gap-10">
            {Object.entries(
              libraryData.reduce((acc: any, curr: any) => {
                const groupTitle = curr.title || 'Obras Desconhecidas';
                if (!acc[groupTitle]) acc[groupTitle] = [];
                acc[groupTitle].push(curr);
                return acc;
              }, {})
            ).map(([mangaTitle, chapters]: [string, any]) => {
              const sortedChapters = [...chapters].sort((a, b) => {
                const numA = parseFloat(a.chapter) || 0;
                const numB = parseFloat(b.chapter) || 0;
                return numA - numB;
              });

              return (
                <MangaAccordion 
                  key={mangaTitle} 
                  mangaTitle={mangaTitle} 
                  chapters={sortedChapters} 
                />
              );
            })}
          </div>
        ) : (
          <div className="p-12 text-center text-foreground-muted bg-panel border border-panel-light rounded-2xl flex flex-col items-center justify-center">
            <BookMarked size={48} className="text-panel-light mb-4 opacity-50" />
            <p className="text-lg">Você ainda não tem nenhum mangá salvo localmente.</p>
            <p className="text-sm mt-2">Clique em "Baixar Novo" para adicionar um capítulo.</p>
          </div>
        )}
      </div>

      {/* SEARCH MODAL */}
      <Modal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        title="Baixar Novo Capítulo"
      >
        <div className="text-center mb-6">
          <p className="text-foreground-muted text-sm">Cole a URL do MangaDex ou o ID do capítulo para iniciar a tradução automática.</p>
        </div>

        <form onSubmit={handleStart} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-foreground-muted">
              <Search size={18} />
            </div>
            <input
              type="text"
              placeholder="https://mangadex.org/chapter/..."
              className="w-full bg-base border border-panel-light rounded-lg py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-foreground transition-all"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="text-foreground-muted text-sm">Idioma da Imagem (Source):</label>
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              className="bg-base border border-panel-light rounded-lg py-2 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              disabled={isLoading}
            >
              <option value="auto">Auto (MangaDex)</option>
              <option value="ENG">Inglês</option>
              <option value="SPA">Espanhol</option>
              <option value="JPN">Japonês</option>
              <option value="KOR">Coreano</option>
              <option value="POR">Português</option>
            </select>
          </div>

          {error && <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={isLoading || !inputUrl.trim()}
            className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50"
          >
            {isLoading ? <><Loader2 className="animate-spin mr-2" size={18} /> Iniciando...</> : (chapters.length > 0 ? 'Atualizar Capítulos' : 'Buscar / Iniciar')}
          </button>
        </form>

        {chapters.length > 0 && (
          <div className="mt-6 max-h-64 overflow-y-auto pr-2 space-y-2 border-t border-panel-light pt-4 custom-scrollbar relative">
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-sm font-bold text-foreground">Capítulos Encontrados</h4>
              <button
                type="button"
                onClick={() => {
                  if (selectedChapters.size === chapters.length) {
                    setSelectedChapters(new Set());
                  } else {
                    setSelectedChapters(new Set(chapters.map(c => c.id)));
                  }
                }}
                className="text-xs text-primary hover:underline"
              >
                {selectedChapters.size === chapters.length ? 'Desmarcar todos' : 'Marcar todos'}
              </button>
            </div>
            {chapters.map((chapter) => (
              <label
                key={chapter.id}
                className={`w-full text-left p-3 rounded-lg bg-base border ${selectedChapters.has(chapter.id) ? 'border-primary bg-primary/10' : 'border-panel-light hover:border-primary/50'} transition-colors flex justify-between items-center group cursor-pointer`}
              >
                <div className="flex items-center truncate pr-4">
                  <input
                    type="checkbox"
                    className="hidden"
                    checked={selectedChapters.has(chapter.id)}
                    onChange={() => {
                      const newSelected = new Set(selectedChapters);
                      if (newSelected.has(chapter.id)) {
                        newSelected.delete(chapter.id);
                      } else {
                        newSelected.add(chapter.id);
                      }
                      setSelectedChapters(newSelected);
                    }}
                  />
                  <div className="mr-3 text-primary">
                    {selectedChapters.has(chapter.id) ? <CheckSquare size={18} /> : <Square size={18} className="text-foreground-muted" />}
                  </div>
                  <div className="truncate">
                    <span className="font-bold text-foreground mr-2">Ch. {chapter.chapter}</span>
                    <span className="text-sm text-foreground-muted truncate">{chapter.title || 'Sem título'}</span>
                  </div>
                </div>
                <span className="text-xs uppercase bg-panel px-2 py-1 rounded text-foreground-muted whitespace-nowrap group-hover:bg-primary/20 group-hover:text-primary transition-colors">
                  {chapter.language || 'UNK'}
                </span>
              </label>
            ))}
            {selectedChapters.size > 0 && (
              <div className="sticky bottom-0 pt-2 bg-panel/80 backdrop-blur-sm">
                <button
                  type="button"
                  onClick={async () => {
                    setIsLoading(true);
                    try {
                      await startBulkDownload.mutateAsync({
                        chapterIds: Array.from(selectedChapters),
                        sourceLang
                      });
                      setSelectedChapters(new Set());
                      setIsSearchModalOpen(false);
                      queryClient.invalidateQueries({ queryKey: ['library'] });
                    } catch (err: any) {
                      setError(err.message || 'Failed to start bulk download');
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  disabled={isLoading}
                  className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors shadow-lg"
                >
                  Baixar {selectedChapters.size} Capítulos Selecionados
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
