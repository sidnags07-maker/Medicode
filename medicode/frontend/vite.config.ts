import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/walker": "http://localhost:8000",
      "/user": "http://localhost:8000",
      "/api": "http://localhost:8000",
    },
  },
});
