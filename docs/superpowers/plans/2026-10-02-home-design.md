# Home Screen Design & Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Overhaul the Home screen to serve as a user's Library, displaying a beautifully designed list of saved/translated chapters, based on the layout and tokens specified in `apps/web/design.pen`.

**Architecture:** 
- Add a new backend endpoint `GET /api/manga/library` to scan the `/data` folder (and metadata/Redis) to list downloaded chapters.
- Expand the frontend `Home.tsx` to display this library.
- Use Atomic Design components matching the `.pen` tokens (colors: `#121212`, `#1A1A1A`, `#9D4EDD`, font: `Inter`).

**Tech Stack:** React 19, Tailwind CSS, TanStack React Query, FastAPI (Python).

**Spec:** Frontend Design Upgrade & Local Library API.

---

### Task 0: Design the Home Screen in Pencil

**Interfaces:**
- Consumes: The `apps/web/design.pen` file.
- Produces: Visual design in `.pen` for the full Home Screen and Library section.

- [ ] **Step 1: Setup Pencil Workspace**
Use the `pencil` MCP tool (`get_app_state`, `execute`) to target `apps/web/design.pen`.
Find the "Home Screen" frame (id: `yx6si`) and ensure we have an empty space to layout the new elements, or modify the frame directly using `FindEmptySpace` and `Insert`.

- [ ] **Step 2: Execute JS Snippet to build the UI**
Using the `pencil` MCP's `execute` tool, build the layout of the Home Screen to match our new specification (including the Search Box at the top and the "Sua Biblioteca" section below it). Add a few mock `Chapter Item` references inside it to test the flexbox `gap` and `padding`.

- [ ] **Step 3: Capture Screenshot**
End the execution snippet with `TakeScreenshot(["yx6si"])` to verify the visual fidelity of the generated UI. If it looks wrong, use the `execute`'s `edits` parameter to fix it.

- [ ] **Step 4: Commit**
```bash
git add apps/web/design.pen
git commit -m "design: create home screen library mockups in design.pen"
```

---

### Task 1: Create Mock Data for the Library (Frontend-only)

**Files:**
- Modify: `apps/web/src/api.ts`
- Modify: `apps/web/src/hooks/useManga.ts`

**Interfaces:**
- Produces: A mocked `getLibrary` function returning a fake array of chapters to unblock the UI design while the backend is refactored.

- [ ] **Step 1: Add Mock API hook in Frontend**
In `apps/web/src/api.ts`, add the fetcher returning mock data:
```typescript
  getLibrary: async () => {
    // MOCK DATA: Remove this once the backend endpoint is ready
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          library: [
            {
              id: "mock-1",
              title: "A New Alliance",
              chapter: "13",
              downloaded: 24,
              total: 24
            },
            {
              id: "mock-2",
              title: "The Beginning",
              chapter: "12",
              downloaded: 10,
              total: 20
            }
          ]
        });
      }, 500); // simulate network latency
    });
  },
```

- [ ] **Step 2: Add React Query hook**
In `apps/web/src/hooks/useManga.ts`, add:
```typescript
export const useLibrary = () => {
  return useQuery({
    queryKey: ['library'],
    queryFn: api.getLibrary,
  });
};
```

- [ ] **Step 3: Commit**
```bash
git add apps/web/src/api.ts apps/web/src/hooks/useManga.ts
git commit -m "feat: add mocked library endpoint and frontend hooks to unblock UI"
```

---

### Task 2: Create Atomic Components for Library Design

**Files:**
- Create: `apps/web/src/components/molecules/LibraryCard.tsx`
- Modify: `apps/web/tailwind.config.js` (Ensure colors match `design.pen`)

**Interfaces:**
- Consumes: Tailwind classes and Lucide icons.
- Produces: `LibraryCard` molecule based on `design.pen`'s "Chapter Item 13".

- [ ] **Step 1: Check Tailwind Config**
Ensure `tailwind.config.js` (or inline classes) supports colors from `design.pen`:
- `bg-base`: `#121212`
- `bg-panel`: `#1A1A1A`
- `accent`: `#9D4EDD`

- [ ] **Step 2: Create LibraryCard Molecule**
Build exactly what `design.pen` outlines:
```tsx
// apps/web/src/components/molecules/LibraryCard.tsx
import { Link } from 'react-router-dom';

interface LibraryCardProps {
  id: string;
  title: string;
  chapter: string;
  downloaded: number;
  total: number;
}

export const LibraryCard = ({ id, title, chapter, downloaded, total }: LibraryCardProps) => {
  return (
    <div className="w-full h-20 bg-base rounded-2xl px-6 flex justify-between items-center border border-panel-light hover:border-primary/50 transition-colors">
      <div className="flex gap-6 items-center">
        <span className="text-foreground-muted font-bold text-lg">Ch. {chapter}</span>
        <div className="flex flex-col gap-1">
          <span className="text-foreground font-semibold text-base">{title || "Unknown Title"}</span>
          <span className="text-foreground-muted text-sm font-normal">
            Baixado: {downloaded}/{total} páginas • PT-BR
          </span>
        </div>
      </div>
      
      <Link 
        to={`/reader/${id}`}
        className="h-10 bg-[#333333] hover:bg-[#444] rounded-full px-6 flex justify-center items-center transition-colors"
      >
        <span className="text-foreground font-semibold text-sm">Ler</span>
      </Link>
    </div>
  );
};
```

- [ ] **Step 3: Commit**
```bash
git add apps/web/src/components/molecules/LibraryCard.tsx
git commit -m "feat: add LibraryCard molecule matching design.pen specs"
```

---

### Task 3: Revamp Home Page

**Files:**
- Modify: `apps/web/src/pages/Home.tsx`

**Interfaces:**
- Consumes: `useLibrary`, `LibraryCard`, Existing Search Form.
- Produces: The new Home screen that features the Library below the search box.

- [ ] **Step 1: Refactor Home.tsx**
```tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, BookMarked } from 'lucide-react';
import { api } from '@/api';
import { useStartDownload, useLibrary } from '@/hooks/useManga';
import { LibraryCard } from '@/components/molecules/LibraryCard';
import { Loader } from '@/components/atoms/Loader';

export function Home() {
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
      
      {/* SEARCH SECTION */}
      <div className="w-full bg-panel rounded-2xl shadow-xl overflow-hidden border border-panel-light p-8">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold mb-2">Read Manga</h2>
          <p className="text-foreground-muted text-sm">Enter a MangaDex Chapter ID or Manga URL.</p>
        </div>

        <form onSubmit={handleStart} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-foreground-muted">
              <Search size={18} />
            </div>
            <input
              type="text"
              placeholder="https://mangadex.org/title/..."
              className="w-full bg-base border border-panel-light rounded-lg py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-foreground transition-all"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {error && <div className="p-3 rounded-lg bg-red-500/10 text-red-400 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={isLoading || !inputUrl.trim()}
            className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-3 px-4 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50"
          >
            {isLoading ? <><Loader2 className="animate-spin mr-2" size={18} /> Processing...</> : (chapters.length > 0 ? 'Refresh Chapters' : 'Start / Fetch')}
          </button>
        </form>
      </div>
      
      {/* LIBRARY SECTION */}
      <div className="w-full flex flex-col gap-4 mb-20">
        <div className="flex items-center gap-2 mb-2">
          <BookMarked className="text-primary" size={24} />
          <h2 className="text-xl font-bold text-foreground">Sua Biblioteca</h2>
        </div>
        
        {libraryLoading ? (
          <Loader message="Carregando obras salvas..." />
        ) : libraryData?.library?.length > 0 ? (
          <div className="flex flex-col gap-4">
            {libraryData.library.map((item: any) => (
              <LibraryCard 
                key={item.id}
                id={item.id}
                title={item.title}
                chapter={item.chapter}
                downloaded={item.downloaded}
                total={item.total}
              />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-foreground-muted bg-panel border border-panel-light rounded-2xl">
            Você ainda não tem nenhum mangá salvo localmente.
          </div>
        )}
      </div>

    </div>
  );
}
```

- [ ] **Step 2: Build & Lint Check**
Run `pnpm --filter web run build` and `pnpm --filter web lint`.

- [ ] **Step 3: Commit**
```bash
git add apps/web/src/pages/Home.tsx
git commit -m "feat: redesign home screen to feature saved chapters library"
```
