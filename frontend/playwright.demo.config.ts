import { defineConfig, devices } from "@playwright/test";

// Dedicated config for recording demo videos.
// Assumes the app is already running (frontend :5173, backend :4040).
export default defineConfig({
  testDir: "./e2e/demo",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 600000,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1440, height: 900 },
    video: { mode: "on", size: { width: 1440, height: 900 } },
    actionTimeout: 30000,
    launchOptions: { slowMo: 350 },
  },
  // Override the device's 1280x720 viewport so the page fills the 1440x900
  // video canvas (otherwise the recording has gray padding on the edges).
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
});
