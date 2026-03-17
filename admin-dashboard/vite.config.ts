import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    port: 5173,
  },
  css: {
    preprocessorOptions: {
      less: {
        modifyVars: {
          '@brand-color': '#0052D9',
        },
        javascriptEnabled: true,
      },
    },
  },
})
