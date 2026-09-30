import { Queue, Worker, Job } from 'bullmq';
import IORedis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

// BullMQ requires enableReadyCheck: false and maxRetriesPerRequest: null
// when providing a raw IORedis instance.
export const createRedisConnection = () =>
  new IORedis(REDIS_URL, {
    enableReadyCheck: false,
    maxRetriesPerRequest: null,
  });

export const pageQueue = new Queue('page-processing', {
  connection: createRedisConnection(),
});

const WORKER_ML_URL = process.env.WORKER_ML_URL || 'http://localhost:8000';

export const createPageWorker = () => {
  return new Worker(
    'page-processing',
    async (job: Job) => {
      const { chapterId, url, pageIndex } = job.data;

      const response = await fetch(`${WORKER_ML_URL}/process-page`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          chapterId,
          pageId: String(pageIndex),
        }),
      });

      if (!response.ok) {
        throw new Error(`ML Worker error: ${response.status} ${response.statusText}`);
      }

      return response.json();
    },
    {
      connection: createRedisConnection(),
      concurrency: 3,
    }
  );
};
