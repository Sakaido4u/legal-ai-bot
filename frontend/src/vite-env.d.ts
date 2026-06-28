/// <reference types="vite/client" />

// This file tells TypeScript about Vite-specific globals.
// The triple-slash directive pulls in all of Vite's type definitions
// including ImportMeta, import.meta.env, import.meta.hot, etc.

// Declare your custom environment variables here.
// This gives you full autocomplete and type safety on import.meta.env
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_ENV: 'development' | 'production' | 'test'
  // Add more VITE_ variables here as you add them to .env
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}