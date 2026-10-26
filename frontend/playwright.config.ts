import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const testDirectory = mkdtempSync(join(tmpdir(), "parser-browser-test-"));
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8010",
    headless: true,
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox"],
    },
  },
  webServer: {
    command:
      "../.venv/bin/uvicorn backend.app.api:app --app-dir .. --host 127.0.0.1 --port 8010 --no-access-log",
    url: "http://127.0.0.1:8010/api/health",
    reuseExistingServer: false,
    env: { DATABASE_URL: "sqlite:///" + join(testDirectory, "browser.db") },
  },
});
