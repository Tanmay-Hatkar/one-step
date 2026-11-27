import { defineConfig, devices } from "@playwright/test";

// The first-run flow against the real API and a production build of the web app.
// The API runs with no OpenAI key, so written diffs come from the code template:
// deterministic, free, and the same path users get if the model is down.
const API_PORT = 8000;
const WEB_PORT = 3000;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    ...devices["Pixel 7"],
    trace: "retain-on-failure",
    launchOptions: process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH }
      : {},
  },
  webServer: [
    {
      command: `uv run uvicorn app.main:app --port ${API_PORT}`,
      cwd: "../api",
      url: `http://localhost:${API_PORT}/health`,
      env: { OPENAI_API_KEY: "", SENTRY_DSN: "", DATABASE_URL: "sqlite:///./e2e.db" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `npx next start -p ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
