# Frontend Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the React frontend into an Atomic Design pattern, adopt TanStack React Query for declarative data fetching/polling, and configure import aliases.

**Architecture:** 
- Break down monolithic components (`Reader.tsx`) into Atomic components (atoms, molecules, organisms, templates).
- Migrate from raw `useEffect` `fetch` polling to `@tanstack/react-query` using `useQuery` (with `refetchInterval`) and `useMutation`.
- Clean up imports with `vite-tsconfig-paths` and TypeScript path aliases (`@/*`).

**Tech Stack:** React 19, TypeScript, Vite, TanStack React Query, Tailwind CSS, Lucide React.

**Spec:** Frontend Technical Debt Refactoring & Data Fetching Overhaul.

## Global Constraints

- Run `pnpm --filter web lint` and `pnpm --filter web test` frequently.
- Follow functional component patterns and avoid class components.
- Do not change API contract or backend logic.

---

### Task 1: Setup Aliases and React Query Dependencies

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/tsconfig.json`
- Modify: `apps/web/vite.config.ts`
- Modify: `apps/web/src/main.tsx`

**Interfaces:**
- Consumes: Existing Vite app.
- Produces: Application wrapped in `QueryClientProvider` and supporting `@/*` imports.

- [ ] **Step 1: Install dependencies**
```bash
pnpm --filter web add @tanstack/react-query
pnpm --filter web add -D vite-tsconfig-paths
```

- [ ] **Step 2: Configure TypeScript paths**
Add `baseUrl` and `paths` to `apps/web/tsconfig.json` (or `tsconfig.app.json` depending on Vite structure):
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

- [ ] **Step 3: Configure Vite Aliases**
Modify `apps/web/vite.config.ts`:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
});
```

- [ ] **Step 4: Setup QueryClientProvider in main.tsx**
```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 5: Verify build**
Run: `pnpm --filter web build`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add apps/web
git commit -m "chore: setup tanstack query and path aliases"
```

---

### Task 2: Create Custom Hooks for API (React Query)

**Files:**
- Create: `apps/web/src/hooks/useManga.ts`

**Interfaces:**
- Consumes: `apps/web/src/api.ts`
- Produces: `useChapterStatus`, `useStartDownload`, `useClearCache`

- [ ] **Step 1: Create Custom Hooks File**
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ChapterStatus } from '@/api';

export const useStartDownload = () => {
  return useMutation({
    mutationFn: api.startDownload,
  });
};

export const useChapterStatus = (chapterId: string | undefined, isPolling: boolean) => {
  return useQuery<ChapterStatus, Error>({
    queryKey: ['chapterStatus', chapterId],
    queryFn: () => {
      if (!chapterId) throw new Error("No chapter ID");
      return api.getStatus(chapterId);
    },
    enabled: !!chapterId,
    refetchInterval: isPolling ? 1000 : false,
  });
};

export const useClearCache = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.clearCache,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chapterStatus'] });
    },
  });
};
```

- [ ] **Step 2: Commit**
```bash
git add apps/web/src/hooks
git commit -m "feat: create react-query hooks for manga api"
```

---

### Task 3: Extract Atomic Components (Atoms & Molecules)

**Files:**
- Create: `apps/web/src/components/atoms/ProgressBar.tsx`
- Create: `apps/web/src/components/atoms/Button.tsx`
- Create: `apps/web/src/components/atoms/Loader.tsx`
- Create: `apps/web/src/components/molecules/ErrorCard.tsx`
- Create: `apps/web/src/components/molecules/LoadingStatus.tsx`

**Interfaces:**
- Consumes: Tailwind classes and Lucide icons.
- Produces: Reusable UI elements for the Reader page.

- [ ] **Step 1: Create ProgressBar Atom**
```tsx
// apps/web/src/components/atoms/ProgressBar.tsx
export const ProgressBar = ({ percent }: { percent: number }) => (
  <div className="w-full bg-panel-light rounded-full h-2">
    <div
      className="bg-primary h-2 rounded-full transition-all duration-500"
      style={{ width: `${percent}%` }}
    />
  </div>
);
```

- [ ] **Step 2: Create Loader Atom**
```tsx
// apps/web/src/components/atoms/Loader.tsx
import { Loader2 } from 'lucide-react';

export const Loader = ({ message }: { message?: string }) => (
  <div className="flex flex-col items-center justify-center p-8 gap-4 text-foreground-muted">
    <Loader2 size={30} className="animate-spin text-primary" />
    {message && <span className="text-sm">{message}</span>}
  </div>
);
```

- [ ] **Step 3: Create ErrorCard Molecule**
```tsx
// apps/web/src/components/molecules/ErrorCard.tsx
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
```

- [ ] **Step 4: Create LoadingStatus Molecule**
```tsx
// apps/web/src/components/molecules/LoadingStatus.tsx
import { Loader2 } from 'lucide-react';
import { ProgressBar } from '@/components/atoms/ProgressBar';

interface LoadingStatusProps {
  completed: number;
  total: number;
}

export const LoadingStatus = ({ completed, total }: LoadingStatusProps) => {
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const remaining = total - completed;

  return (
    <div className="mt-20 flex flex-col items-center gap-6 text-foreground-muted px-4 w-full max-w-sm mx-auto">
      <Loader2 size={40} className="animate-spin text-primary" />
      <div className="w-full space-y-2">
        <div className="flex justify-between text-sm">
          <span>Traduzindo páginas...</span>
          <span className="text-primary font-semibold">{completed} / {total}</span>
        </div>
        <ProgressBar percent={percent} />
        <p className="text-xs text-center text-foreground-muted">
          {remaining} página{remaining !== 1 ? 's' : ''} restante{remaining !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};
```

- [ ] **Step 5: Check typescript build**
Run `pnpm --filter web run build`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add apps/web/src/components
git commit -m "feat: extract atomic components for reader"
```

---

### Task 4: Refactor Reader Page to use React Query & Atomic Components

**Files:**
- Modify: `apps/web/src/pages/Reader.tsx`
- Modify: `apps/web/src/components/Reader.tsx` -> `apps/web/src/components/organisms/ReaderComponent.tsx` (Move and rename import aliases)

**Interfaces:**
- Consumes: `useChapterStatus`, `useStartDownload`, Atoms, Molecules.
- Produces: The fully functioning Reader page with simplified logic.

- [ ] **Step 1: Move Reader Component**
```bash
mkdir -p apps/web/src/components/organisms
mv apps/web/src/components/Reader.tsx apps/web/src/components/organisms/ReaderComponent.tsx
```

- [ ] **Step 2: Refactor `pages/Reader.tsx`**
Refactor the file to remove `useEffect` polling and use the new custom hooks and atomic components.

```tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings } from 'lucide-react';
import { useChapterStatus, useStartDownload } from '@/hooks/useManga';
import ReaderComponent from '@/components/organisms/ReaderComponent';
import { ErrorCard } from '@/components/molecules/ErrorCard';
import { LoadingStatus } from '@/components/molecules/LoadingStatus';
import { Loader } from '@/components/atoms/Loader';
// ... Settings Drawer can remain inline or be extracted as an Organism ...

export default function ReaderPage() {
  const { chapterId } = useParams<{ chapterId: string }>();
  const navigate = useNavigate();
  
  const [readingDirection, setReadingDirection] = useState<'webtoon' | 'paged'>('webtoon');
  const [imageFit, setImageFit] = useState<'width' | 'height'>('width');
  const [loadingMode, setLoadingMode] = useState<'real-time' | 'wait'>('real-time');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);

  const startDownload = useStartDownload();
  const [shouldPoll, setShouldPoll] = useState(true);

  const { data: status, error: queryError, isLoading } = useChapterStatus(chapterId, shouldPoll);

  useEffect(() => {
    if (chapterId) {
      startDownload.mutate(chapterId);
    }
  }, [chapterId]);

  useEffect(() => {
    if (status?.status === 'done' || status?.status === 'error') {
      setShouldPoll(false);
    }
  }, [status]);

  const error = queryError?.message || status?.error;
  const isPolling = shouldPoll;
  const totalPages = status?.total || 0;
  const completed = status?.completed || 0;
  const readyPages = status?.readyPages || [];
  
  const pages = loadingMode === 'real-time' 
    ? readyPages.map(pageIndex => `/data/${chapterId}/${pageIndex}.png`)
    : (status?.status === 'done' ? Array.from({ length: totalPages }, (_, i) => `/data/${chapterId}/${i + 1}.png`) : []);

  const progressPercent = totalPages > 0 ? ((currentPageIndex + 1) / totalPages) * 100 : 0;

  return (
    <div className="min-h-screen bg-base flex flex-col">
       {/* ... Header ... */}
       {/* Use ErrorCard, LoadingStatus, Loader, ProgressBar where appropriate */}
       {/* ... Settings ... */}
    </div>
  );
}
```
*(Ensure all imports and paths in `ReaderPage` are fully replaced and correct).*

- [ ] **Step 3: Update Home.tsx and RootLayout.tsx**
Update imports in `RootLayout.tsx` to use `@/api` or `@/hooks/useManga`.

- [ ] **Step 4: Verify integration**
Run `pnpm --filter web run build` and `pnpm --filter web lint`.

- [ ] **Step 5: Commit**
```bash
git add apps/web
git commit -m "refactor: integrate react-query and atomic design into reader page"
```
