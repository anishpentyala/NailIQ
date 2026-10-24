/* global process -- vite.config runs in Node, not the browser eslint env */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Phone testing over the home Wi-Fi: `PHONE_HTTPS=1 npm run dev` serves HTTPS on the LAN (iOS only allows the camera on
// HTTPS) using the local certificate in data/phone_test_certs (see docs/PHONE_TESTING.md). Off by default.
const phone = Boolean(process.env.PHONE_HTTPS)
const certDir = fileURLToPath(new URL('../data/phone_test_certs', import.meta.url))

// Lets the phone download the (name-constrained, key-deleted) local CA to install it.
const serveCa = () => ({
  name: 'serve-local-ca',
  configureServer(server) {
    server.middlewares.use('/nailiq-ca.crt', (_req, res) => {
      res.setHeader('Content-Type', 'application/x-x509-ca-cert')
      res.end(fs.readFileSync(path.join(certDir, 'ca.crt')))
    })
  },
})

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), ...(phone ? [serveCa()] : [])],
  server: {
    port: Number(process.env.PORT) || 5173,
    strictPort: true,
    ...(phone && {
      host: true,
      https: {
        key: fs.readFileSync(path.join(certDir, 'server.key')),
        cert: fs.readFileSync(path.join(certDir, 'server.crt')),
      },
    }),
    // The browser calls the API on its own origin; Vite forwards these paths to the Flask backend.
    allowedHosts: true,
    proxy: Object.fromEntries(
      ['/analyze', '/validate_photo', '/history', '/feedback'].map((p) => [p, `http://127.0.0.1:${process.env.API_PORT || 5000}`]),
    ),
  },
})
