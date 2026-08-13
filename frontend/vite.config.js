import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base defaults to the local FastAPI dev server (uvicorn
// aci.api.app:app --reload, port 8000). Override with VITE_API_BASE if the
// backend runs elsewhere — never a hardcoded remote URL.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
