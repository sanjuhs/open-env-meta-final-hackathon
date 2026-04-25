import { defineConfig } from "vite";

const apiPort = process.env.PORT || "8791";

export default defineConfig({
  server: {
    watch: {
      ignored: ["**/.venv/**", "**/.uv-cache/**", "**/.cache/**"]
    },
    proxy: {
      "/api": `http://localhost:${apiPort}`
    }
  }
});
