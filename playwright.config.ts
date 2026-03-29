import { defineConfig } from 'playwright/test';

export default defineConfig({
  testDir: 'test/e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:4319',
    trace: 'retain-on-failure',
  },
});
