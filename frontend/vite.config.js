/* global process -- vite.config runs in Node, not the browser eslint env */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 5173,
    strictPort: true,
    // Phone testing: an HTTPS tunnel (random hostname) points at this server; the API paths go to the Flask backend.
    allowedHosts: true,
    proxy: Object.fromEntries(
      ['/analyze', '/validate_photo', '/history', '/feedback'].map((p) => [p, `http://127.0.0.1:${process.env.API_PORT || 5000}`]),
    ),
  },
})
