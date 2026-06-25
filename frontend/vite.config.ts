import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the frontend can call it during dev
// without CORS or hardcoded ports in the client code. The backend routes are
// already namespaced under /api (e.g. /api/reviews), so the path is forwarded
// unchanged (no rewrite).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
