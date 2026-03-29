import { appendFile, mkdtemp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { beforeEach, describe, expect, it } from 'vitest';

import { appendEvent, readEvents } from '../../src/core/event-store';
import { ensureStoragePaths, getStoragePaths, sessionEventFile } from '../../src/core/storage';

let root: string;

beforeEach(async () => {
  root = await mkdtemp(path.join(os.tmpdir(), 'rcaio-storage-'));
});

describe('event store', () => {
  it('reads valid events and ignores trailing partial lines', async () => {
    const paths = getStoragePaths(root);
    await ensureStoragePaths(paths);
    await appendEvent(paths, {
      sessionId: 'ses_1',
      sequence: 1,
      type: 'session.started',
      createdAt: new Date().toISOString(),
      source: { adapterId: 'fake' },
      data: {},
    });
    await appendFile(sessionEventFile(paths, 'ses_1'), '{"bad": true', 'utf8');
    const events = await readEvents(paths, 'ses_1');
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe('session.started');
  });
});
