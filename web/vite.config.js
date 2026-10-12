import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, Vite serves the pages and passes API and socket traffic to
// the Python server on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
