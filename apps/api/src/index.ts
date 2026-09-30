import { Effect } from 'effect';
import express from 'express';
import { fetchChapterPages } from './mangadex.ts';
import { pageQueue, chapterQueue, flowProducer, createPageWorker, createChapterWorker } from './queue.ts';

const createServer = Effect.sync(() => {
  const app = express();
  app.use(express.json());

  app.use('/data', express.static('/data'));

  app.get('/api/manga/:mangaId/chapters', async (req, res) => {
    const { mangaId } = req.params;
    try {
      const { fetchMangaFeed } = await import('./mangadex.ts');
      const chapters = await Effect.runPromise(fetchMangaFeed(mangaId));
      res.json({ chapters });
    } catch (err) {
      res.status(500).json({ status: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
    }
  });

  app.post('/api/manga/:chapterId', async (req, res) => {
    const { chapterId } = req.params;
    try {
      // Clean previous jobs
      const [prevPages, prevChapters] = await Promise.all([
        pageQueue.getJobs(['completed', 'failed', 'active', 'waiting']),
        chapterQueue.getJobs(['completed', 'failed', 'active', 'waiting', 'waiting-children']),
      ]);
      await Promise.all([
        ...prevPages.filter(j => j.data?.chapterId === chapterId).map(j => j.remove().catch(() => {})),
        ...prevChapters.filter(j => j.data?.chapterId === chapterId).map(j => j.remove().catch(() => {})),
      ]);

      const pages = await Effect.runPromise(fetchChapterPages(chapterId));

      const flow = await flowProducer.add({
        name: 'process-chapter',
        queueName: 'chapter-processing',
        data: { chapterId },
        children: pages.map((page) => ({
          name: 'process-page',
          queueName: 'page-processing',
          data: {
            chapterId,
            url: page.url,
            pageIndex: page.pageIndex,
            filename: page.filename,
          },
        })),
      });

      res.json({
        status: 'queued',
        chapterId,
        totalPages: pages.length,
        parentJobId: flow.job.id,
      });
    } catch (err) {
      res.status(500).json({ status: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
    }
  });

  app.get('/api/manga/:chapterId/status', async (req, res) => {
    const { chapterId } = req.params;
    try {
      const chapterJobs = await chapterQueue.getJobs(['completed', 'active', 'waiting', 'failed', 'waiting-children']);
      const parentJob = chapterJobs.find(j => j.data?.chapterId === chapterId);

      if (!parentJob) {
        return res.json({ chapterId, total: 0, completed: 0, failed: 0, status: 'not_found' });
      }

      const deps = await parentJob.getDependencies({ processed: true, unprocessed: true });
      const processedCount = Object.keys(deps.processed || {}).length;
      const unprocessedCount = (deps.unprocessed || []).length;
      const total = processedCount + unprocessedCount;

      const failedPageJobs = await pageQueue.getJobs(['failed']);
      const failed = failedPageJobs.filter(j => j.data?.chapterId === chapterId).length;

      const parentState = await parentJob.getState();
      let status: string;
      if (parentState === 'completed') status = 'done';
      else if (failed > 0 || parentState === 'failed') status = 'error';
      else status = 'processing';

      res.json({ chapterId, total, completed: processedCount, failed, status });
    } catch (err) {
      res.status(500).json({ status: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
    }
  });

  return app;
});

const startServer = (app: express.Express) => Effect.async<never, Error, void>((resume) => {
  const port = process.env.PORT || 3000;
  const server = app.listen(port, () => {
    console.log(`API running on port ${port}`);
    resume(Effect.succeed(undefined) as any);
  });
  server.on('error', (err) => { resume(Effect.fail(err)); });
});

export const main = Effect.gen(function* () {
  const app = yield* createServer;
  createPageWorker();
  createChapterWorker();
  yield* startServer(app);
});

if (import.meta.url === `file://${process.argv[1]}`) {
  Effect.runPromise(main).catch(console.error);
}

export { createServer, startServer };
