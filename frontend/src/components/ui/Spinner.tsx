import { cn } from '@/utils/cn'

export function Spinner({ size = 'md', className }: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        'animate-spin rounded-full',
        'border-2 border-[var(--border)] border-t-[var(--accent)]',
        size === 'sm' && 'h-4 w-4',
        size === 'md' && 'h-6 w-6',
        size === 'lg' && 'h-10 w-10',
        className,
      )}
    />
  )
}

export function PageLoader() {
  return (
    <div className="fixed inset-0 z-50 bg-[var(--bg)]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-4">
      <Spinner size="lg" />
      <p className="text-sm text-[var(--text-muted)] animate-pulse">Analyzing legal compliance...</p>
    </div>
  )
}