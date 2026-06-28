import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'
import { cn } from '@/utils/cn'

interface ThemeToggleProps {
  className?: string
  size?: 'sm' | 'md'
}

export function ThemeToggle({ className, size = 'md' }: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn(
        'relative inline-flex items-center justify-center rounded-lg',
        'border border-[var(--border)] bg-[var(--bg-surface)]',
        'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-raised)]',
        'transition-all duration-150 focus-visible:outline-none',
        'focus-visible:ring-2 focus-visible:ring-[var(--accent)]',
        size === 'md' ? 'h-9 w-9' : 'h-7 w-7',
        className,
      )}
    >
      <Sun
        className={cn(
          'absolute transition-all duration-200',
          size === 'md' ? 'h-[18px] w-[18px]' : 'h-3.5 w-3.5',
          isDark ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 rotate-90 scale-75',
        )}
      />
      <Moon
        className={cn(
          'absolute transition-all duration-200',
          size === 'md' ? 'h-[18px] w-[18px]' : 'h-3.5 w-3.5',
          isDark ? 'opacity-0 -rotate-90 scale-75' : 'opacity-100 rotate-0 scale-100',
        )}
      />
    </button>
  )
}