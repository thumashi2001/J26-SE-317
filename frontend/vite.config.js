import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development, any request starting with /api is forwarded to the Express backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:3000',
    },
  },
});
