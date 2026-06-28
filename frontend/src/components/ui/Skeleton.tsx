import { cn } from '@/utils/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}

export function SkeletonCard() {
  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-5/6" />
        <Skeleton className="h-3.5 w-4/6" />
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  const cols = [1, 3, 2, 1, 1]
  return (
    <div className="space-y-0">
      <div className="flex gap-4 px-5 py-3 border-b border-[var(--border)] bg-[var(--bg-raised)]">
        {cols.map((_, i) => <div key={i} className="flex-1"><Skeleton className="h-3.5 w-3/4" /></div>)}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 px-5 py-3.5 border-b border-[var(--border)]">
          {cols.map((_, c) => <div key={c} className="flex-1"><Skeleton className="h-3.5 w-5/6" /></div>)}
        </div>
      ))}
    </div>
  )
}

export function SkeletonStats() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="card space-y-3">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <Skeleton className="h-3.5 w-1/2" />
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-3 w-3/4" />
            </div>
            <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
          </div>
        </div>
      ))}
    </div>
  )
}