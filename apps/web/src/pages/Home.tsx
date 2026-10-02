import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, BookMarked, Plus } from 'lucide-react';
import { useStartDownload, useLibrary } from '@/hooks/useManga';
import { LibraryCard } from '@/components/molecules/LibraryCard';
import { Loader } from '@/components/atoms/Loader';
import { Modal } from '@/components/atoms/Modal';

export function Home() {
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [inputUrl, setInputUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  
  const navigate = useNavigate();
  const startDownload = useStartDownload();
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
        await startDownload.mutateAsync(extractedId);
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
          <div className="flex flex-col gap-4">
            {libraryData.map((item: any) => (
              <LibraryCard 
                key={item.id}
                id={item.id}
                title={item.title}
                chapter={item.chapter}
                downloaded={typeof item.downloaded === 'boolean' ? (item.downloaded ? item.total : 0) : item.downloaded}
                total={item.total}
              />
            ))}
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

          {error && <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={isLoading || !inputUrl.trim()}
            className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50"
          >
            {isLoading ? <><Loader2 className="animate-spin mr-2" size={18} /> Iniciando Tradução...</> : (chapters.length > 0 ? 'Refresh Chapters' : 'Buscar / Iniciar')}
          </button>
        </form>
      </Modal>
    </div>
  );
}
