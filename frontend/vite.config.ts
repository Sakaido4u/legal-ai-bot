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
        // Split vendor code into separate chunks for better caching
        manualChunks: {
          vendor:   ['react', 'react-dom', 'react-router-dom'],
          charts:   ['recharts'],
          motion:   ['framer-motion'],
          ui:       ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
})