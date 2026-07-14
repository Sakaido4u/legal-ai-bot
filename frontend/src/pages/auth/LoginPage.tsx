import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { Button }      from '@/components/ui/Button'
import { Input }       from '@/components/ui/Input'
import { useAuth }     from '@/context/AuthContext'
import { authService } from '@/services/authService'
import { ROUTES }      from '@/constants/app'
import toast           from 'react-hot-toast'

// ── Validation schema ─────────────────────────────────────────
const loginSchema = z.object({
  email:    z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

// ── Component ─────────────────────────────────────────────────
export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [authError,    setAuthError]    = useState<string | null>(null)

  const { login }   = useAuth()
  const navigate    = useNavigate()
  const location    = useLocation()

  // Redirect back to the page they were trying to access
  const from =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ??
    ROUTES.DASHBOARD

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  // ── Submit ───────────────────────────────────────────────────
  const onSubmit = async (data: LoginFormData) => {
    // Clear any previous auth error on new submit attempt
    setAuthError(null)

    try {
      const response = await authService.login({
        email:    data.email,
        password: data.password,
      })

      // Successful login — store user + token in AuthContext & localStorage
      login(
        {
          id:    response.user.id,
          name:  response.user.name,
          email: response.user.email,
          is_admin: response.user.is_admin ?? false,
        },
        response.access_token
      )

      toast.success(`Welcome back, ${response.user.name}!`)
      navigate(from, { replace: true })

    } catch (err: unknown) {
      let message = 'Invalid email or password'

      if (err && typeof err === 'object') {
        const axiosErr = err as {
          code?: string
          response?: { status?: number; data?: { detail?: string; message?: string } }
          message?: string
        }

        if (
          axiosErr.code === 'ERR_NETWORK' ||
          axiosErr.message?.includes("Can't reach the server")
        ) {
          message =
            "Can't reach the server — check that the API is running and try again shortly."
        } else if (axiosErr.response?.status === 401 || axiosErr.response?.status === 403) {
          message = 'Invalid email or password'
        } else if (axiosErr.response?.data?.detail) {
          message = axiosErr.response.data.detail
        } else if (axiosErr.response?.data?.message) {
          message = axiosErr.response.data.message
        } else if (axiosErr.message && axiosErr.message !== 'Network Error') {
          message = axiosErr.message
        } else if (axiosErr.message === 'Network Error') {
          message =
            "Can't reach the server — check that the API is running and try again shortly."
        }
      }

      setAuthError(message)
    }
  }

  // ── Render ───────────────────────────────────────────────────
  return (
    <div className="space-y-6">

      {/* Heading */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-[var(--text)]">Welcome back</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Sign in to your LexAI account
        </p>
      </div>

      {/* Auth error banner — only shown after a failed login attempt */}
      {authError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 p-3.5 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
        >
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-400 font-medium">
            {authError}
          </p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <Input
          label="Email address"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          autoFocus
          error={errors.email?.message}
          leftElement={<Mail className="w-4 h-4" />}
          {...register('email')}
        />

        <Input
          label="Password"
          type={showPassword ? 'text' : 'password'}
          placeholder="Enter your password"
          autoComplete="current-password"
          error={errors.password?.message}
          leftElement={<Lock className="w-4 h-4" />}
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword(p => !p)}
              className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword
                ? <EyeOff className="w-4 h-4" />
                : <Eye    className="w-4 h-4" />
              }
            </button>
          }
          {...register('password')}
        />

        <div className="flex justify-end">
          <Link
            to={ROUTES.FORGOT}
            className="text-xs text-brand-600 hover:text-brand-700 hover:underline transition-colors"
          >
            Forgot password?
          </Link>
        </div>

        <Button
          type="submit"
          className="w-full"
          isLoading={isSubmitting}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      {/* Demo credentials hint */}
      <div className="rounded-xl bg-[var(--bg-raised)] border border-[var(--border)] p-4">
        <p className="text-xs font-semibold text-[var(--text)] mb-2">
          Demo credentials
        </p>
        <div className="space-y-1">
          <p className="text-xs text-[var(--text-muted)] font-mono">
            demo@lexai.com / Demo@1234
          </p>
          <p className="text-xs text-[var(--text-muted)] font-mono">
            admin@lexai.com / Admin@1234
          </p>
        </div>
      </div>

      {/* Sign up link */}
      <p className="text-sm text-center text-[var(--text-muted)]">
        Don&apos;t have an account?{' '}
        <Link
          to={ROUTES.REGISTER}
          className="text-brand-600 font-medium hover:underline"
        >
          Create one
        </Link>
      </p>
    </div>
  )
}