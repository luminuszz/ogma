import { Effect } from 'effect';
import express from 'express';

const createServer = Effect.sync(() => {
  const app = express();
  
  // Serve static files from /data
  app.use('/data', express.static('/data'));

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
  yield* startServer(app);
});

// Run if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  Effect.runPromise(main).catch(console.error);
}

export { createServer, startServer };
