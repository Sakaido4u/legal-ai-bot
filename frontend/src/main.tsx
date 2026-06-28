import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// Import global styles — must be here, not in App.tsx
// Using a relative path from main.tsx which is in src/
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)