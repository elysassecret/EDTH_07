import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:18870",
    viewport: { width: 1440, height: 1000 },
    launchOptions: { args: ["--enable-unsafe-swiftshader"] },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "uv run python -m server --serve-web --demo --no-log --host 127.0.0.1 --port 18870",
    cwd: "..",
    url: "http://127.0.0.1:18870",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
