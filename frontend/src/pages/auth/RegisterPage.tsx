import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { User, Mail, Lock } from 'lucide-react'
import { Button }  from '@/components/ui/Button'
import { Input }   from '@/components/ui/Input'
import { useAuth } from '@/context/AuthContext'
import { ROUTES }  from '@/constants/app'
import toast       from 'react-hot-toast'

const registerSchema = z.object({
  name:            z.string().min(2, 'Name must be at least 2 characters'),
  email:           z.string().email('Enter a valid email'),
  password:        z.string()
                     .min(8, 'At least 8 characters')
                     .regex(/[A-Z]/, 'Include at least one uppercase letter')
                     .regex(/[0-9]/, 'Include at least one number'),
  confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

type RegisterFormData = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { login } = useAuth()
  const navigate  = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({ resolver: zodResolver(registerSchema) })

  const onSubmit = async (data: RegisterFormData) => {
    await new Promise(r => setTimeout(r, 800))
    login({ id: '1', name: data.name, email: data.email }, 'mock-token')
    toast.success(`Welcome to LexAI, ${data.name}!`)
    navigate(ROUTES.DASHBOARD)
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-[var(--text)]">Create your account</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Start analyzing legal documents in minutes
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <Input
          label="Full name"
          placeholder="Jane Smith"
          error={errors.name?.message}
          leftElement={<User className="w-4 h-4" />}
          {...register('name')}
        />
        <Input
          label="Email"
          type="email"
          placeholder="you@example.com"
          error={errors.email?.message}
          leftElement={<Mail className="w-4 h-4" />}
          {...register('email')}
        />
        <Input
          label="Password"
          type="password"
          placeholder="Min. 8 chars"
          hint="Include uppercase and a number"
          error={errors.password?.message}
          leftElement={<Lock className="w-4 h-4" />}
          {...register('password')}
        />
        <Input
          label="Confirm password"
          type="password"
          placeholder="Repeat password"
          error={errors.confirmPassword?.message}
          leftElement={<Lock className="w-4 h-4" />}
          {...register('confirmPassword')}
        />
        <Button type="submit" className="w-full" isLoading={isSubmitting}>
          Create account
        </Button>
      </form>

      <p className="text-sm text-center text-[var(--text-muted)]">
        Already have an account?{' '}
        <Link to={ROUTES.LOGIN} className="text-brand-600 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}