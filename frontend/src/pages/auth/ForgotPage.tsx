import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft, CheckCircle, KeyRound } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input }  from '@/components/ui/Input'
import { ROUTES } from '@/constants/app'
import { authService } from '@/services/authService'
import toast      from 'react-hot-toast'

const emailSchema = z.object({
  email: z.string().email('Enter a valid email address'),
})
type EmailForm = z.infer<typeof emailSchema>

const resetSchema = z.object({
  token: z.string().min(10, 'Paste the reset token'),
  new_password: z.string().min(6, 'Password must be at least 6 characters'),
})
type ResetForm = z.infer<typeof resetSchema>

export function ForgotPage() {
  const [step, setStep] = useState<'request' | 'reset' | 'done'>('request')
  const [devToken, setDevToken] = useState<string | null>(null)

  const emailForm = useForm<EmailForm>({ resolver: zodResolver(emailSchema) })
  const resetForm = useForm<ResetForm>({ resolver: zodResolver(resetSchema) })

  const onRequest = async (data: EmailForm) => {
    try {
      const res = await authService.forgotPassword(data.email)
      if (res.reset_token) {
        setDevToken(res.reset_token)
        resetForm.setValue('token', res.reset_token)
        toast.success('Reset token issued (dev mode)')
      } else {
        toast.success(res.message)
      }
      setStep('reset')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Request failed')
    }
  }

  const onReset = async (data: ResetForm) => {
    try {
      await authService.resetPassword(data.token, data.new_password)
      toast.success('Password updated')
      setStep('done')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Reset failed')
    }
  }

  if (step === 'done') {
    return (
      <div className="text-center space-y-4">
        <div className="w-14 h-14 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center mx-auto">
          <CheckCircle className="w-7 h-7 text-green-600" />
        </div>
        <h1 className="text-xl font-bold text-[var(--text)]">Password updated</h1>
        <p className="text-sm text-[var(--text-muted)]">
          You can log in with your new password.
        </p>
        <Link to={ROUTES.LOGIN}>
          <Button variant="outline" className="w-full">Back to Login</Button>
        </Link>
      </div>
    )
  }

  if (step === 'reset') {
    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-[var(--text)]">Set a new password</h1>
          <p className="text-sm text-[var(--text-muted)]">
            {devToken
              ? 'Dev mode: token was returned by the API (no email provider).'
              : 'Paste the reset token from your email, then choose a new password.'}
          </p>
        </div>
        <form onSubmit={resetForm.handleSubmit(onReset)} noValidate className="space-y-4">
          <Input
            label="Reset token"
            error={resetForm.formState.errors.token?.message}
            leftElement={<KeyRound className="w-4 h-4" />}
            {...resetForm.register('token')}
          />
          <Input
            label="New password"
            type="password"
            error={resetForm.formState.errors.new_password?.message}
            {...resetForm.register('new_password')}
          />
          <Button type="submit" className="w-full" isLoading={resetForm.formState.isSubmitting}>
            Update password
          </Button>
        </form>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Link
          to={ROUTES.LOGIN}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text)] mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to login
        </Link>
        <h1 className="text-2xl font-bold text-[var(--text)]">Reset your password</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Enter your email and we&apos;ll issue a reset token.
        </p>
      </div>

      <form onSubmit={emailForm.handleSubmit(onRequest)} noValidate className="space-y-4">
        <Input
          label="Email address"
          type="email"
          placeholder="you@example.com"
          error={emailForm.formState.errors.email?.message}
          leftElement={<Mail className="w-4 h-4" />}
          {...emailForm.register('email')}
        />
        <Button type="submit" className="w-full" isLoading={emailForm.formState.isSubmitting}>
          Send reset link
        </Button>
      </form>
    </div>
  )
}
