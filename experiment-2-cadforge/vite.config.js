import { defineConfig } from "vite";

export default defineConfig({
  server: {
    watch: {
      ignored: ["**/.venv/**", "**/.uv-cache/**", "**/.cache/**"]
    },
    proxy: {
      "/api": "http://localhost:8791"
    }
  }
});
