/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { compression, defineAlgorithm } from 'vite-plugin-compression2'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Writes a .gz copy next to each text file in dist, so nginx's
    // gzip_static can send it as-is instead of recompressing on every
    // request (see nginx.conf). Photos and woff/woff2 fonts are already
    // compressed, so they're left out.
    compression({
      algorithms: [defineAlgorithm('gzip', { level: 9 })],
      include:
        /\.(html|css|js|mjs|json|svg|txt|xml|webmanifest|ico|ttf|otf|eot|wasm)$/,
    }),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
