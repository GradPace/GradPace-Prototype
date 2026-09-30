import { defineConfig, devices } from '@playwright/test'

// Targets the existing docker-compose.dev.yml dev stack (sqlite-based - dev
// has no Postgres). The stack is started/stopped by `make test-e2e`, not by
// Playwright's own `webServer` option - see the Makefile for the
// bring-up/health-wait/teardown sequence and the backend/db.sqlite3 wipe
// that keeps the self-hosted runner's disk from growing run over run.
export default defineConfig({
  testDir: './tests',
  // The dev backend runs on sqlite (see docker-compose.dev.yml), which
  // throws "database is locked" under concurrent writers - run tests
  // serially against it rather than in parallel workers.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
