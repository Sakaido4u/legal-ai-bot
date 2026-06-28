import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { Button }   from '@/components/ui/Button'
import { Input }    from '@/components/ui/Input'
import { useAuth }  from '@/context/AuthContext'
import { ROUTES }   from '@/constants/app'
import toast        from 'react-hot-toast'

const loginSchema = z.object({
  email:    z.string().min(1, 'Email is required').email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

type LoginFormData = z.infer<typeof loginSchema>

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const from = (location.state as { from?: { pathname: string } } | null)
    ?.from?.pathname ?? ROUTES.DASHBOARD

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginFormData) => {
    try {
      // Simulate API call — replace with real backend call later
      await new Promise(res => setTimeout(res, 800))
      login(
        { id: '1', name: 'Demo User', email: data.email },
        'mock-jwt-token-12345'
      )
      toast.success('Welcome back!')
      navigate(from, { replace: true })
    } catch {
      toast.error('Login failed. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      {/* Heading */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-[var(--text)]">Welcome back</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Sign in to your LexAI account
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <Input
          label="Email address"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          error={errors.email?.message}
          leftElement={<Mail className="w-4 h-4" />}
          {...register('email')}
        />

        <Input
          label="Password"
          type={showPassword ? 'text' : 'password'}
          placeholder="••••••••"
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
                : <Eye className="w-4 h-4" />}
            </button>
          }
          {...register('password')}
        />

        <div className="flex justify-end">
          <Link
            to={ROUTES.FORGOT}
            className="text-xs text-brand-600 hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <Button
          type="submit"
          className="w-full"
          isLoading={isSubmitting}
        >
          Sign in
        </Button>
      </form>

      {/* Demo credentials hint */}
      <div className="rounded-lg bg-[var(--bg-raised)] border border-[var(--border)] p-3">
        <p className="text-xs text-[var(--text-muted)] text-center">
          <span className="font-medium text-[var(--text)]">Demo:</span>{' '}
          Use any email + any password (6+ chars)
        </p>
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