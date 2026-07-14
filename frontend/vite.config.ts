import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      // '@/' maps to 'src/' — lets you write:
      //   import { cn } from '@/utils/cn'
      // instead of:
      //   import { cn } from '../../../utils/cn'
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 3000,
    // Proxy API calls during dev so you avoid CORS issues.
    // '/api/v1/compliance' → 'http://localhost:8000/v1/compliance'
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
    },
  },

  build: {
    // Raise the warning threshold slightly — legal text can be verbose
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Vite 8 / Rollup typing expects a function (object map form is rejected by TS)
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          if (id.includes('recharts')) return 'charts'
          if (id.includes('framer-motion')) return 'motion'
          if (id.includes('@radix-ui')) return 'ui'
          if (
            id.includes('react-router') ||
            id.includes('react-dom') ||
            id.includes(`${path.sep}react${path.sep}`) ||
            id.includes('/react/')
          ) {
            return 'vendor'
          }
        },
      },
    },
  },
})