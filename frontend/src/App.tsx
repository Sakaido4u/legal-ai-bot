import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider }  from '@/context/AuthContext'
import { AppRouter }     from '@/routes/AppRouter'
import { Toaster }       from 'react-hot-toast'

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRouter />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'var(--bg-surface)',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: '0.75rem',
              fontSize: '0.875rem',
              padding: '12px 16px',
              boxShadow: '0 4px 12px rgb(0 0 0 / 0.15)',
            },
            success: {
              iconTheme: { primary: '#22C55E', secondary: '#FFFFFF' },
            },
            error: {
              iconTheme: { primary: '#EF4444', secondary: '#FFFFFF' },
            },
          }}
        />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App