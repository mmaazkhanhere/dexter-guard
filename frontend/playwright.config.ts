import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  webServer: [
    { command: "npm run dev -- --host 127.0.0.1 --port 4173", url: "http://127.0.0.1:4173", reuseExistingServer: true },
    { command: "uv run python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000", cwd: "../backend", url: "http://127.0.0.1:8000/api/v1/health", reuseExistingServer: true },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
