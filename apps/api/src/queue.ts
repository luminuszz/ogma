import { Queue, Worker, Job } from 'bullmq';

const connection = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10),
};

export const createQueue = (name: string) => {
  return new Queue(name, { connection });
};

export const createWorker = (name: string, processor: (job: Job) => Promise<any>) => {
  return new Worker(name, processor, { connection });
};

export const myQueue = createQueue('mainQueue');
export const myWorker = createWorker('mainQueue', async (job) => {
  console.log(`Processing job ${job.id}`);
  return { status: 'done' };
});
