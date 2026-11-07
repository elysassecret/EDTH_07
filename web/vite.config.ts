import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Owner: C. The scene JSON lives in ../data and is bundled at build time (no runtime fetch).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5173, fs: { allow: [".."] } },
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 3000,
    rolldownOptions: {
      input: {
        dashboard: fileURLToPath(new URL("./index.html", import.meta.url)),
        viewer: fileURLToPath(new URL("./viewer.html", import.meta.url)),
      },
    },
  },
});
