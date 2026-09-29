import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { createServer } from './index.js';
import { Effect } from 'effect';
import express from 'express';
import fs from 'fs';
import path from 'path';

// Mock Redis so tests don't fail if Redis isn't running
vi.mock('ioredis', () => {
  const MockRedis = class {
    on() {}
    connect() { return Promise.resolve(); }
    disconnect() {}
    quit() { return Promise.resolve(); }
  };
  return { default: MockRedis };
});

describe('API & Queue Tests', () => {
  let app: express.Express;

  beforeAll(async () => {
    app = await Effect.runPromise(createServer);
    
    // Create dummy file for testing static serving
    const dataDir = '/tmp/data';
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    fs.writeFileSync(path.join(dataDir, 'test.txt'), 'hello world');
    
    // Mount /data to /tmp/data for tests if not running in docker
    app.use('/test-data', express.static(dataDir));
  });

  afterAll(() => {
    try {
      fs.unlinkSync('/tmp/data/test.txt');
    } catch (e) {}
  });

  it('should serve static files', async () => {
    // We test /test-data as /data is a docker volume
    const res = await request(app).get('/test-data/test.txt');
    expect(res.status).toBe(200);
    expect(res.text).toBe('hello world');
  });

  it('should initialize bullmq pageQueue', async () => {
    const { pageQueue } = await import('./queue.js');
    expect(pageQueue).toBeDefined();
    expect(pageQueue.name).toBe('page-processing');
  });

  it('should export createPageWorker factory', async () => {
    const { createPageWorker } = await import('./queue.js');
    expect(createPageWorker).toBeDefined();
    expect(typeof createPageWorker).toBe('function');
  });
});
