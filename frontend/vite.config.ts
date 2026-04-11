import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Если фронт и бэк на разных порталах — понадобятся CORS (уже настроены в бэке)
export default defineConfig({
  plugins: [react()],
  css: {
    preprocessorOptions: {
      scss: {
        api: "modern-compiler",
      },
    },
  },
  server: {
    port: 5173,
  },
});
