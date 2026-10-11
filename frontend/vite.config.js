// Vite's defaults are right for this project; only two things need saying.
//
// `base: "./"` makes the build work from a file path as well as a server root, which is the
// fallback if the demo machine has no working dev server on the day.
// The dev server port is PINNED to 5173 rather than left to auto-increment: the backend's CORS
// list names that port, and a silent shift to 5174 would fail every request with a browser
// message that does not mention the port.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173, strictPort: true },
});
