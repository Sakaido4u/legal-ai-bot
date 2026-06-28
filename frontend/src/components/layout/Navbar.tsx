import { Menu, Bell, Search } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { cn } from '@/utils/cn'

interface NavbarProps {
  onMenuClick: () => void
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const { user, logout } = useAuth()

  return (
    <header
      className={cn(
        'h-14 shrink-0 flex items-center gap-3 px-4',
        'bg-[var(--bg-surface)] border-b border-[var(--border)]',
      )}
    >
      {/* Mobile hamburger */}
      <button
        onClick={onMenuClick}
        aria-label="Toggle sidebar"
        className="p-1.5 rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)] transition-colors lg:hidden"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Search bar */}
      <div className="flex-1 max-w-sm">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)] pointer-events-none" />
          <input
            type="search"
            placeholder="Search analyses..."
            className={cn(
              'w-full h-8 rounded-md text-sm pl-8 pr-3',
              'bg-[var(--bg-raised)] border border-[var(--border)]',
              'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
              'focus:outline-none focus:ring-1 focus:ring-[var(--accent)] focus:border-[var(--accent)]',
              'focus:bg-[var(--bg-surface)] transition-all duration-150',
            )}
          />
        </div>
      </div>

      <div className="flex-1" />

      {/* Actions */}
      <div className="flex items-center gap-1">
        <ThemeToggle size="sm" />

        {/* Notification bell */}
        <button
          aria-label="Notifications"
          className="relative p-1.5 rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)] transition-colors"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-red-500 border-2 border-[var(--bg-surface)]" />
        </button>

        {/* Divider + User */}
        <div className="flex items-center gap-2 ml-1 pl-3 border-l border-[var(--border)]">
          <div
            className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold shrink-0 select-none"
            title={user?.name}
          >
            {user?.name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          {user && (
            <div className="hidden md:flex flex-col items-start">
              <span className="text-xs font-medium text-[var(--text)] leading-none max-w-[100px] truncate">
                {user.name}
              </span>
              <button
                onClick={logout}
                className="text-[0.65rem] text-[var(--text-muted)] hover:text-red-500 transition-colors mt-0.5 leading-none"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}