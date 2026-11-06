import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Owner: C. The scene JSON lives in ../data and is bundled at build time (no runtime fetch).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, fs: { allow: [".."] } },
  build: { outDir: "dist", chunkSizeWarningLimit: 3000 },
});
