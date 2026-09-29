import { Queue, Worker, Job } from 'bullmq';

const connection = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10),
};

export const pageQueue = new Queue('page-processing', { connection });

const WORKER_ML_URL = process.env.WORKER_ML_URL || 'http://localhost:8000';

export const createPageWorker = () => {
  return new Worker(
    'page-processing',
    async (job: Job) => {
      const { chapterId, url, pageIndex, filename } = job.data;

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

      const result = await response.json();
      return result;
    },
    {
      connection,
      concurrency: 3,
    }
  );
};
