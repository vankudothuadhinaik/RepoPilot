import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 20_000,
  retries: 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:4173", browserName: "chromium", headless: true },
  webServer: { command: "npm run preview -- --host 127.0.0.1", port: 4173, reuseExistingServer: !process.env.CI, timeout: 30_000 },
});
