import { type HTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils/cn'
import { type RiskLevel } from '@/constants/app'

const badgeVariants = cva('badge', {
  variants: {
    variant: {
      default:  'bg-[var(--bg-raised)] text-[var(--text-muted)]',
      primary:  'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
      success:  'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      warning:  'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      danger:   'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      outline:  'border border-[var(--border)] text-[var(--text-muted)]',
    },
  },
  defaultVariants: { variant: 'default' },
})

interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean
}

export function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', {
          'bg-brand-500': variant === 'primary',
          'bg-green-500': variant === 'success',
          'bg-amber-500': variant === 'warning',
          'bg-red-500':   variant === 'danger',
          'bg-slate-400': !variant || variant === 'default' || variant === 'outline',
        })} />
      )}
      {children}
    </span>
  )
}

const RISK_CONFIG: Record<RiskLevel, { label: string; variant: BadgeProps['variant'] }> = {
  high:   { label: 'High Risk',   variant: 'danger' },
  medium: { label: 'Medium Risk', variant: 'warning' },
  low:    { label: 'Low Risk',    variant: 'success' },
  none:   { label: 'No Risk',     variant: 'default' },
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const { label, variant } = RISK_CONFIG[level]
  return <Badge variant={variant} dot>{label}</Badge>
}