import { defineConfig, devices } from "@playwright/test";

// Dedicated config for recording demo videos.
// Assumes the app is already running (frontend :5173, backend :4040).
export default defineConfig({
  testDir: "./e2e/demo",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 240000,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1440, height: 900 },
    video: { mode: "on", size: { width: 1440, height: 900 } },
    actionTimeout: 30000,
    launchOptions: { slowMo: 350 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
