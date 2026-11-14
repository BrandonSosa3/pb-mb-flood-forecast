import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // The map chunk (MapLibre, ~800 kB) is loaded only when the map opens.
  build: { chunkSizeWarningLimit: 900 },
});
