import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2',
    'rounded-lg font-medium text-sm select-none',
    'transition-all duration-150',
    'focus-visible:outline-none focus-visible:ring-2',
    'focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2',
    'focus-visible:ring-offset-[var(--bg)]',
    'disabled:pointer-events-none disabled:opacity-50',
  ],
  {
    variants: {
      variant: {
        primary:   ['bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 shadow-sm'],
        secondary: ['bg-[var(--bg-raised)] text-[var(--text)] border border-[var(--border)]',
                    'hover:bg-[var(--bg-surface)] hover:border-[var(--border-strong)]'],
        ghost:     ['text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)]'],
        danger:    ['bg-red-600 text-white hover:bg-red-700 active:bg-red-800'],
        outline:   ['border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg-raised)]',
                    'hover:border-[var(--border-strong)]'],
        link:      ['text-brand-600 underline-offset-4 hover:underline p-0 h-auto'],
      },
      size: {
        sm:   'h-8 px-3 text-xs',
        md:   'h-9 px-4',
        lg:   'h-11 px-6 text-base',
        icon: 'h-9 w-9 p-0',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading = false, leftIcon, rightIcon, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 className="h-4 w-4 animate-spin shrink-0" />}
      {!isLoading && leftIcon}
      {children}
      {!isLoading && rightIcon}
    </button>
  )
)
Button.displayName = 'Button'
export { buttonVariants }