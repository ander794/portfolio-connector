import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Bundles mcp-app.html + its JS (incl. the @modelcontextprotocol/ext-apps SDK)
// into ONE self-contained HTML file — no external/CDN requests, so it renders
// inside Claude's sandboxed iframe.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    target: "es2020",
    rollupOptions: { input: "mcp-app.html" },
  },
});
