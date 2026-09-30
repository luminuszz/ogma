import { pageQueue } from './queue.ts';
async function flush() {
  await pageQueue.obliterate({ force: true });
  console.log("Queue flushed!");
  process.exit(0);
}
flush();
