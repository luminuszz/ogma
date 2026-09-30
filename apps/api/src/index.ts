import { Effect } from 'effect';
import express from 'express';
import { fetchChapterPages } from './mangadex.ts';
import { pageQueue, createPageWorker } from './queue.ts';

const createServer = Effect.sync(() => {
  const app = express();
  app.use(express.json());

  // Serve static files from /data
  app.use('/data', express.static('/data'));

  // Queue a chapter for processing
  app.post('/api/manga/:chapterId', async (req, res) => {
    const { chapterId } = req.params;
    try {
      const pages = await Effect.runPromise(fetchChapterPages(chapterId));

      const jobs = await Promise.all(
        pages.map((page) =>
          pageQueue.add('process-page', {
            chapterId,
            url: page.url,
            pageIndex: page.pageIndex,
            filename: page.filename,
          })
        )
      );

      res.json({
        status: 'queued',
        chapterId,
        totalPages: pages.length,
        jobIds: jobs.map((j) => j.id),
      });
    } catch (err) {
      res.status(500).json({
        status: 'error',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  });

  // Get chapter processing status
  app.get('/api/manga/:chapterId/status', async (req, res) => {
    const { chapterId } = req.params;
    try {
      const jobs = await pageQueue.getJobs(['completed', 'active', 'waiting', 'failed']);
      const chapterJobs = jobs.filter((j) => j.data?.chapterId === chapterId);
      const completed = chapterJobs.filter((j) => j.finishedOn).length;
      const total = chapterJobs.length;

      res.json({
        chapterId,
        total,
        completed,
        status: total === 0 ? 'not_found' : completed === total ? 'done' : 'processing',
      });
    } catch (err) {
      res.status(500).json({
        status: 'error',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  });

  return app;
});

const startServer = (app: express.Express) => Effect.async<never, Error, void>((resume) => {
  const port = process.env.PORT || 3000;
  const server = app.listen(port, () => {
    console.log(`API running on port ${port}`);
    resume(Effect.succeed(undefined));
  });

  server.on('error', (err) => {
    resume(Effect.fail(err));
  });
});

export const main = Effect.gen(function* () {
  const app = yield* createServer;
  createPageWorker();
  yield* startServer(app);
});

// Run if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  Effect.runPromise(main).catch(console.error);
}

export { createServer, startServer };

