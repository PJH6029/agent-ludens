import { mkdtemp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { beforeEach, describe, expect, it } from 'vitest';

import { loadConfig, saveConfig } from '../../src/core/config';
import { ensureStoragePaths, getStoragePaths } from '../../src/core/storage';

let root: string;

beforeEach(async () => {
  root = await mkdtemp(path.join(os.tmpdir(), 'rcaio-config-'));
});

describe('config', () => {
  it('creates a default config when missing', async () => {
    const paths = getStoragePaths(root);
    await ensureStoragePaths(paths);
    const config = await loadConfig(paths);
    expect(config.server.host).toBe('127.0.0.1');
    expect(config.agents.defaultAgentId).toBe('fake');
  });

  it('persists custom settings', async () => {
    const paths = getStoragePaths(root);
    await ensureStoragePaths(paths);
    const config = await loadConfig(paths);
    config.server.port = 9999;
    await saveConfig(config, paths);
    const reloaded = await loadConfig(paths);
    expect(reloaded.server.port).toBe(9999);
  });
});
