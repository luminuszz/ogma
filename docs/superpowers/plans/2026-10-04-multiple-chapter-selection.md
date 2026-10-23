# Multiple Chapter Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to select multiple chapters from the MangaDex search results modal and dispatch them all for background translation simultaneously.

**Architecture:** We will introduce a new state `selectedChapters` (a `Set` of chapter IDs) in `Home.tsx`. The chapter list buttons will transform into toggleable rows with checkboxes. A new bulk-action button will trigger `Promise.all` over the selected IDs, sending multiple API requests to `startDownload`, and then refresh the Library view without navigating to a specific reader.

**Tech Stack:** React, TailwindCSS, TanStack Query

**Spec:** User Request: "vamos implementar uma feature na tela no modal de baixar selecionar capitulo para traduzir, devera ter um checkbox para selecoanr multiplo e enviar para o back-end todos os capitulos que queremos traduduzir"

## Global Constraints

- Do not navigate to the Reader page when downloading multiple chapters. Keep the user on the Home page so they can see the Library update.
- Ensure the checkbox UI aligns with the existing Tailwind design system (`bg-primary`, `border-panel-light`, etc.).

---

### Task 1: Backend - Bulk Download Endpoint

**Files:**
- Modify: `apps/api/src/main.py`

**Interfaces:**
- Produces: `POST /api/manga/bulk` receiving `{"chapterIds": ["uuid1", "uuid2"], "sourceLang": "auto"}`

- [ ] **Step 1: Create the Bulk Request Model**

Add a Pydantic model for the request payload in `main.py`:
```python
from pydantic import BaseModel

class BulkDownloadRequest(BaseModel):
    chapterIds: list[str]
    sourceLang: str = "auto"
```

- [ ] **Step 2: Create the `/api/manga/bulk` endpoint**

In `main.py`, add the endpoint. It should iterate over `request.chapterIds` and essentially run the same setup logic as `process_chapter` for each ID (fetch pages, meta, save to DB, enqueue). You can extract the core logic or simply await it in a loop.

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/main.py
git commit -m "feat(api): add bulk download endpoint for multiple chapters"
```

### Task 2: Frontend - UI Checkboxes & Bulk Dispatch

**Files:**
- Modify: `apps/web/src/pages/Home.tsx`
- Modify: `apps/web/src/api.ts`
- Modify: `apps/web/src/hooks/useManga.ts`

**Interfaces:**
- Consumes: `POST /api/manga/bulk`
- Produces: UI with checkboxes, `selectedChapters` state.

- [ ] **Step 1: Add bulk API method**

In `api.ts`, add `startBulkDownload: async (params: { chapterIds: string[]; sourceLang?: string })`.

- [ ] **Step 2: Add hook**

In `hooks/useManga.ts`, add `useStartBulkDownload` using the new api method.

- [ ] **Step 3: Update Home.tsx State**

Add `const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());` to `Home.tsx`. Change the mapped chapters to have an `<input type="checkbox">` and toggle their IDs in the `Set` on click.

- [ ] **Step 4: Add Bulk Dispatch Button**

Below the chapter list, render "Baixar X Capítulos Selecionados". When clicked, call `startBulkDownload.mutateAsync`, close the modal, reset selections, and invalidate the `['library']` query (using `useQueryClient`) without navigating away.

- [ ] **Step 5: Run linter and Commit**

```bash
pnpm --filter web lint
git add apps/web/src/pages/Home.tsx apps/web/src/api.ts apps/web/src/hooks/useManga.ts
git commit -m "feat(web): implement chapter multi-selection and bulk download integration"
```
