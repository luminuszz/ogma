# Ogma Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a background pipeline that downloads English mangas from MangaDex, translates them to Portuguese using local models (Ollama/YOLO/OCR/LaMa), and displays them in a React Web Reader.

**Architecture:** Monorepo (Turborepo) with three main services: `api` (TypeScript + Effect.ts + BullMQ), `worker-ml` (Python FastAPI + ML libraries), and `web` (React + TS). Orchestrated via Docker Compose with a shared volume for images, connecting to an external Redis instance on your VPS for queue state.

**Tech Stack:** Node.js, Effect.ts, BullMQ, React, Python, FastAPI, YOLO, PaddleOCR, LaMa, Ollama, External Redis, Docker Compose, Vitest, Pytest, Playwright.

**Spec:** Local conversation

## Global Constraints
- Node Version: >= 20.x
- Python Version: >= 3.10
- Package Manager: pnpm
- GPU Support: Required for local ML (NVIDIA RTX 4070 target)
- Redis: External instance hosted on VPS (no local container)
- No relational DB: Rely on Redis and File System for simplicity.
- Testing: Implement TDD. Node/React use Vitest, Python uses Pytest with FastAPI TestClient (ML models MUST be mocked in tests to run fast without GPU).

---

### Task 1: Monorepo & Infrastructure Scaffolding

**Files:**
- Create: `package.json`
- Create: `turbo.json`
- Create: `pnpm-workspace.yaml`
- Create: `docker-compose.yml`
- Create: `apps/api/package.json`
- Create: `apps/worker-ml/requirements.txt`

**Interfaces:**
- Consumes: None
- Produces: Base monorepo structure and Docker orchestration.

- [ ] **Step 1: Write root configurations**
Create `package.json`, `pnpm-workspace.yaml` defining the `apps/*` workspace, and `turbo.json` for task orchestration.

- [ ] **Step 2: Create docker-compose.yml**
Define the volume `ogma_data` that will be shared between API, ML Worker, and Web for image storage.

- [ ] **Step 3: Setup app placeholders**
Create `apps/api/package.json` and `apps/worker-ml/requirements.txt` with base dependencies (BullMQ, Effect for API; FastAPI, Uvicorn, pytest for Python).

- [ ] **Step 4: Verify workspace**
Run `pnpm install` and ensure workspace links correctly.

- [ ] **Step 5: Commit**
`git commit -m "chore: setup turborepo and docker compose scaffolding"`

---

### Task 2: Python ML Microservice Setup (worker-ml)

**Files:**
- Create: `apps/worker-ml/main.py`
- Create: `apps/worker-ml/test_main.py`
- Create: `apps/worker-ml/Dockerfile`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: Image URLs
- Produces: `POST /process-page` which accepts `{"url": "...", "chapterId": "...", "pageId": "..."}` and returns `{ "status": "ok", "path": "/data/chapterId/pageId.png" }`.

- [ ] **Step 1: Write failing tests in Pytest**
In `test_main.py`, write tests for `/process-page` verifying it accepts the JSON payload, downloads the image (mocked request), and returns the correct path structure.

- [ ] **Step 2: Write FastAPI basic app**
Implement `main.py` with the `/process-page` endpoint. Mock the ML step. Download image and save to `/data/chapterId/pageId.png`. Run pytest to ensure pass.

- [ ] **Step 3: Create Dockerfile for worker-ml**
Ensure it uses a Python base image and installs requirements.

- [ ] **Step 4: Add worker-ml to docker-compose**
Map the `ogma_data` volume to `/data`. Expose port 8000.

- [ ] **Step 5: Commit**
`git commit -m "feat: setup python ml worker baseline and tests"`

---

### Task 3: Node API Setup with Effect.ts & BullMQ

**Files:**
- Create: `apps/api/src/index.ts`
- Create: `apps/api/src/queue.ts`
- Create: `apps/api/src/index.test.ts`
- Create: `apps/api/vitest.config.ts`
- Create: `apps/api/Dockerfile`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: Redis connection.
- Produces: API running on port 3000, connected to BullMQ, with static file serving for `/data`.

- [ ] **Step 1: Setup Vitest & failing tests**
Write tests for API static serving and queue initialization using Vitest.

- [ ] **Step 2: Setup Effect.ts runtime and Express/Fastify server**
In `index.ts`, initialize the web server using Effect to serve static files from `/data`.

- [ ] **Step 3: Initialize BullMQ**
In `queue.ts`, setup the BullMQ Queue and Worker instances connected to Redis. Run tests.

- [ ] **Step 4: Create API Dockerfile & update Compose**
Add the `api` service to `docker-compose.yml`, mapped to the same `ogma_data` volume at `/data`.

- [ ] **Step 5: Commit**
`git commit -m "feat: setup effect.ts api with bullmq, static serving and tests"`

---

### Task 4: MangaDex Integration & Queue Logic

**Files:**
- Create: `apps/api/src/mangadex.ts`
- Create: `apps/api/src/mangadex.test.ts`
- Modify: `apps/api/src/index.ts`
- Modify: `apps/api/src/queue.ts`

**Interfaces:**
- Consumes: MangaDex API `/at-home/server/{chapter_id}`
- Produces: `POST /api/manga/:chapterId` endpoint that queues pages.

- [ ] **Step 1: Write tests for MangaDex fetcher and Queuing**
Implement Vitest tests mocking the MangaDex API response and verifying jobs are added to BullMQ.

- [ ] **Step 2: Write MangaDex fetcher in Effect**
Implement `mangadex.ts` to call MangaDex API and extract high-quality image URLs for a chapter.

- [ ] **Step 3: Add API Endpoint and Queue Worker logic**
Update `index.ts` to add `POST /api/manga/:chapterId`. Update `queue.ts` worker to process jobs: for each page, make an HTTP POST request to the Python `worker-ml` `/process-page` endpoint. Run tests.

- [ ] **Step 4: Commit**
`git commit -m "feat: integrate mangadex and dispatch background jobs with tests"`

---

### Task 5: Python ML Implementation - Computer Vision

**Files:**
- Create: `apps/worker-ml/ml/vision.py`
- Create: `apps/worker-ml/ml/test_vision.py`
- Modify: `apps/worker-ml/main.py`
- Modify: `apps/worker-ml/requirements.txt`

**Interfaces:**
- Consumes: Image file paths.
- Produces: Inpainted image file and a list of detected text areas.

- [ ] **Step 1: Install ML dependencies**
Add OpenCV, Ultralytics (YOLO), PaddleOCR to requirements.

- [ ] **Step 2: Write tests for vision logic**
In `test_vision.py`, test the pipeline structure. Mock YOLO, PaddleOCR, and LaMa so they don't actually run models but return fake bounding boxes and text.

- [ ] **Step 3: Write vision logic**
In `vision.py`, write a function that takes an image path, runs YOLO to find text balloons, runs PaddleOCR to extract English text, and uses OpenCV/LaMa to inpaint the balloon areas. Update `/process-page` to call it. Run tests.

- [ ] **Step 4: Commit**
`git commit -m "feat: implement yolo, ocr and inpainting with mocked tests"`

---

### Task 6: Python ML Implementation - Translation & Typesetting

**Files:**
- Create: `apps/worker-ml/ml/translation.py`
- Create: `apps/worker-ml/ml/typesetting.py`
- Create: `apps/worker-ml/ml/test_translation.py`
- Modify: `apps/worker-ml/main.py`

**Interfaces:**
- Consumes: Extracted English text, local Ollama API.
- Produces: Final translated image with text rendered.

- [ ] **Step 1: Write tests for translation and typesetting**
Mock the HTTP call to Ollama. Verify typesetting correctly uses Pillow functions (mocked or small sample) to draw text.

- [ ] **Step 2: Write translation client and typesetting logic**
Implement `translation.py` calling local Ollama API (Llama 3 8B). Implement `typesetting.py` using Pillow to calculate word-wrap, resize font, and draw translated text. Update `/process-page`. Run tests.

- [ ] **Step 3: Commit**
`git commit -m "feat: implement local ollama translation, typesetting and tests"`

---

### Task 7: React Web Reader Setup (web)

**Files:**
- Create: `apps/web` (via Vite/Next.js)
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: API static images and status polling.
- Produces: User interface for requesting and reading manga.

- [ ] **Step 1: Scaffold React application and test setup**
Initialize a React+TS app inside `apps/web` with Vitest and React Testing Library.

- [ ] **Step 2: Implement Input and Polling UI with tests**
Write tests and implementation for UI that inputs MangaDex Chapter ID, calls the API, and polls for status.

- [ ] **Step 3: Implement Reader UI with tests**
Write tests and implementation for an infinite-scroll or paginated reader component that displays images from `/data/chapterId/pageId.png`.

- [ ] **Step 4: Add web to Compose**
Add the React app to `docker-compose.yml`.

- [ ] **Step 5: Commit**
`git commit -m "feat: build react manga reader web app with unit tests"`

---

### Task 8: End-to-End Pipeline Setup (Playwright)

**Files:**
- Create: `apps/e2e/playwright.config.ts`
- Create: `apps/e2e/tests/reader.spec.ts`

**Interfaces:**
- Consumes: Running docker compose environment.
- Produces: E2E test results validating the whole stack.

- [ ] **Step 1: Setup E2E workspace**
Initialize `apps/e2e` with Playwright dependencies.

- [ ] **Step 2: Write full pipeline E2E test**
In `reader.spec.ts`, write a test that opens the web app, inputs a test chapter ID, waits for processing completion, and verifies the reader displays the processed images.

- [ ] **Step 3: Commit**
`git commit -m "test: implement playwright e2e pipelines"`
