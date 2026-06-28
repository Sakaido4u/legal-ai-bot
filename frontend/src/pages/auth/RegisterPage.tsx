import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { User, Mail, Lock, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { Button }      from '@/components/ui/Button'
import { Input }       from '@/components/ui/Input'
import { useAuth }     from '@/context/AuthContext'
import { authService } from '@/services/authService'
import { ROUTES }      from '@/constants/app'
import toast           from 'react-hot-toast'

// ── Validation schema ─────────────────────────────────────────
const registerSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(60, 'Name is too long'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Enter a valid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must include at least one uppercase letter')
    .regex(/[0-9]/, 'Must include at least one number'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path:    ['confirmPassword'],
})

type RegisterFormData = z.infer<typeof registerSchema>

// ── Component ─────────────────────────────────────────────────
export function RegisterPage() {
  const [authError, setAuthError] = useState<string | null>(null)

  const { login }  = useAuth()
  const navigate   = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  })

  // ── Submit ───────────────────────────────────────────────────
  const onSubmit = async (data: RegisterFormData) => {
    setAuthError(null)

    try {
      const response = await authService.register({
        name:     data.name,
        email:    data.email,
        password: data.password,
      })

      login(
        {
          id:    response.user.id,
          name:  response.user.name,
          email: response.user.email,
        },
        response.access_token
      )

      toast.success(`Welcome to LexAI, ${response.user.name}!`)
      navigate(ROUTES.DASHBOARD, { replace: true })

    } catch (err: unknown) {
      let message = 'Registration failed. Please try again.'

      if (err && typeof err === 'object') {
        const axiosErr = err as {
          response?: { data?: { detail?: string; message?: string } }
          message?: string
        }
        if (axiosErr.response?.data?.detail) {
          message = axiosErr.response.data.detail
        } else if (axiosErr.response?.data?.message) {
          message = axiosErr.response.data.message
        } else if (axiosErr.message && axiosErr.message !== 'Network Error') {
          message = axiosErr.message
        }
      }

      setAuthError(message)
    }
  }

  // ── Render ───────────────────────────────────────────────────
  return (
    <div className="space-y-7">

      {/* Heading — larger, bold, centered */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-extrabold text-[var(--text)] tracking-tight">
          Create your account
        </h1>
        <p className="text-sm text-[var(--text-muted)] leading-relaxed">
          Join LexAI and start analyzing legal documents in minutes.
        </p>
      </div>

      {/* Auth error banner */}
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
          label="Full name"
          placeholder="Jane Smith"
          autoComplete="name"
          autoFocus
          error={errors.name?.message}
          leftElement={<User className="w-4 h-4" />}
          {...register('name')}
        />

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
          type="password"
          placeholder="Min. 8 characters"
          autoComplete="new-password"
          hint="Must include at least one uppercase letter and one number"
          error={errors.password?.message}
          leftElement={<Lock className="w-4 h-4" />}
          {...register('password')}
        />

        <Input
          label="Confirm password"
          type="password"
          placeholder="Repeat your password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          leftElement={<Lock className="w-4 h-4" />}
          {...register('confirmPassword')}
        />

        <div className="pt-1">
          <Button
            type="submit"
            className="w-full"
            isLoading={isSubmitting}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </Button>
        </div>
      </form>

      {/* Sign in link */}
      <p className="text-sm text-center text-[var(--text-muted)]">
        Already have an account?{' '}
        <Link
          to={ROUTES.LOGIN}
          className="text-brand-600 font-semibold hover:underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}