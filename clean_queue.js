const { Queue } = require('bullmq');
const IORedis = require('ioredis');

const connection = new IORedis(process.env.REDIS_URL || 'redis://localhost:6379', {
  enableReadyCheck: false,
  maxRetriesPerRequest: null,
});

const pageQueue = new Queue('page-processing', { connection });

async function clean() {
  console.log("Cleaning failed jobs...");
  await pageQueue.clean(0, 1000, 'failed');
  await pageQueue.clean(0, 1000, 'completed');
  console.log("Cleaned!");
  process.exit(0);
}
clean();
