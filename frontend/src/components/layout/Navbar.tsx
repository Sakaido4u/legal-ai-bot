import { useState, useRef, useEffect, useCallback } from 'react'
import { Menu, Bell, Search, Check, Clock } from 'lucide-react'
import { useAuth }     from '@/context/AuthContext'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { cn }          from '@/utils/cn'

// ── Notification type ─────────────────────────────────────────
interface Notification {
  id:        string
  title:     string
  body:      string
  time:      string
  read:      boolean
  type:      'analysis' | 'risk' | 'system'
}

// ── Mock notifications ─────────────────────────────────────────
const INITIAL_NOTIFICATIONS: Notification[] = [
  {
    id:    'n1',
    title: 'Analysis Complete',
    body:  'GDPR data processing analysis finished with a score of 74.',
    time:  '2 min ago',
    read:  false,
    type:  'analysis',
  },
  {
    id:    'n2',
    title: 'High Risk Detected',
    body:  'Your latest analysis flagged 2 high-risk items in data retention.',
    time:  '1 hr ago',
    read:  false,
    type:  'risk',
  },
  {
    id:    'n3',
    title: 'New Jurisdiction Added',
    body:  'Singapore (SG) legal framework is now available for analysis.',
    time:  '3 hrs ago',
    read:  true,
    type:  'system',
  },
  {
    id:    'n4',
    title: 'Analysis Complete',
    body:  'NDA confidentiality provisions analysis returned 91% compliance.',
    time:  'Yesterday',
    read:  true,
    type:  'analysis',
  },
]

// ── Notification icon color ────────────────────────────────────
const TYPE_STYLES: Record<Notification['type'], string> = {
  analysis: 'bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400',
  risk:     'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
  system:   'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
}

// ── Notification dropdown ──────────────────────────────────────
interface NotificationDropdownProps {
  notifications: Notification[]
  onMarkAllRead: () => void
  onMarkRead:    (id: string) => void
  onClose:       () => void
}

function NotificationDropdown({
  notifications,
  onMarkAllRead,
  onMarkRead,
  onClose,
}: NotificationDropdownProps) {
  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div
      className={cn(
        'absolute right-0 top-full mt-2 z-50',
        'w-[340px] sm:w-[380px]',
        'bg-[var(--bg-surface)] border border-[var(--border)]',
        'rounded-2xl shadow-xl shadow-black/10 dark:shadow-black/30',
        'overflow-hidden',
        'animate-[fade-in_0.15s_ease-out]',
      )}
      // Stop clicks inside the dropdown from closing it
      onClick={e => e.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[var(--text)]">
            Notifications
          </span>
          {unreadCount > 0 && (
            <span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded-full bg-brand-600 text-white text-[10px] font-bold">
              {unreadCount}
            </span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={onMarkAllRead}
            className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            <Check className="w-3 h-3" />
            Mark all read
          </button>
        )}
      </div>

      {/* Notification list */}
      <div className="max-h-[340px] overflow-y-auto">
        {notifications.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
            <Bell className="w-8 h-8 text-[var(--text-subtle)] mb-3" />
            <p className="text-sm font-medium text-[var(--text-muted)]">
              No new notifications.
            </p>
            <p className="text-xs text-[var(--text-subtle)] mt-1">
              You&apos;re all caught up!
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border)]">
            {notifications.map(notif => (
              <li key={notif.id}>
                <button
                  onClick={() => {
                    onMarkRead(notif.id)
                    onClose()
                  }}
                  className={cn(
                    'w-full flex items-start gap-3 px-4 py-3.5 text-left transition-colors',
                    'hover:bg-[var(--bg-raised)]',
                    !notif.read && 'bg-brand-50/50 dark:bg-brand-900/10',
                  )}
                >
                  {/* Type icon */}
                  <div className={cn(
                    'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
                    TYPE_STYLES[notif.type],
                  )}>
                    <Bell className="w-3.5 h-3.5" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={cn(
                        'text-sm leading-snug',
                        notif.read
                          ? 'font-normal text-[var(--text-muted)]'
                          : 'font-semibold text-[var(--text)]',
                      )}>
                        {notif.title}
                      </p>
                      {/* Unread dot */}
                      {!notif.read && (
                        <span className="w-2 h-2 rounded-full bg-brand-600 shrink-0 mt-1" />
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5 leading-relaxed line-clamp-2">
                      {notif.body}
                    </p>
                    <div className="flex items-center gap-1 mt-1.5">
                      <Clock className="w-3 h-3 text-[var(--text-subtle)]" />
                      <span className="text-[11px] text-[var(--text-subtle)]">
                        {notif.time}
                      </span>
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="px-4 py-2.5 border-t border-[var(--border)] bg-[var(--bg-raised)]">
          <button
            onClick={onClose}
            className="text-xs text-brand-600 hover:text-brand-700 font-medium transition-colors w-full text-center"
          >
            View all notifications
          </button>
        </div>
      )}
    </div>
  )
}

// ── Navbar Props ───────────────────────────────────────────────
interface NavbarProps {
  onMenuClick: () => void
}

// ── Main Component ─────────────────────────────────────────────
export function Navbar({ onMenuClick }: NavbarProps) {
  const { user, logout } = useAuth()

  const [notifOpen,      setNotifOpen]      = useState(false)
  const [notifications,  setNotifications]  = useState<Notification[]>(INITIAL_NOTIFICATIONS)

  const bellRef      = useRef<HTMLDivElement>(null)
  const unreadCount  = notifications.filter(n => !n.read).length

  // ── Close dropdown on outside click ─────────────────────────
  const handleOutsideClick = useCallback((e: MouseEvent) => {
    if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
      setNotifOpen(false)
    }
  }, [])

  useEffect(() => {
    if (notifOpen) {
      // Use capture phase so it fires before any inner click handlers
      document.addEventListener('mousedown', handleOutsideClick, true)
    } else {
      document.removeEventListener('mousedown', handleOutsideClick, true)
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick, true)
    }
  }, [notifOpen, handleOutsideClick])

  // ── Close on Escape key ──────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setNotifOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  // ── Mark single notification as read ────────────────────────
  const handleMarkRead = (id: string) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
  }

  // ── Mark all as read ─────────────────────────────────────────
  const handleMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }

  // ── Toggle dropdown ──────────────────────────────────────────
  const toggleNotif = () => setNotifOpen(prev => !prev)

  // ── Render ───────────────────────────────────────────────────
  return (
    <header
      className={cn(
        'h-14 shrink-0 flex items-center gap-3 px-4',
        'bg-[var(--bg-surface)] border-b border-[var(--border)]',
      )}
    >
      {/* Mobile sidebar toggle */}
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
            placeholder="Search analyses…"
            className={cn(
              'w-full h-8 rounded-md text-sm pl-8 pr-3',
              'bg-[var(--bg-raised)] border border-[var(--border)]',
              'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
              'focus:outline-none focus:ring-1 focus:ring-[var(--accent)]',
              'focus:border-[var(--accent)] focus:bg-[var(--bg-surface)]',
              'transition-all duration-150',
            )}
          />
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right actions */}
      <div className="flex items-center gap-1">

        {/* Theme toggle */}
        <ThemeToggle size="sm" />

        {/* ── Notification bell ──────────────────────────── */}
        <div ref={bellRef} className="relative">
          <button
            onClick={toggleNotif}
            aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
            aria-expanded={notifOpen}
            aria-haspopup="true"
            className={cn(
              'relative p-1.5 rounded-md transition-colors',
              'text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)]',
              notifOpen && 'bg-[var(--bg-raised)] text-[var(--text)]',
            )}
          >
            <Bell className="w-4 h-4" />

            {/* Unread badge */}
            {unreadCount > 0 && (
              <span
                className={cn(
                  'absolute -top-0.5 -right-0.5',
                  'flex items-center justify-center',
                  'min-w-[16px] h-4 px-1 rounded-full',
                  'bg-red-500 border-2 border-[var(--bg-surface)]',
                  'text-white text-[9px] font-bold leading-none',
                )}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown */}
          {notifOpen && (
            <NotificationDropdown
              notifications={notifications}
              onMarkAllRead={handleMarkAllRead}
              onMarkRead={handleMarkRead}
              onClose={() => setNotifOpen(false)}
            />
          )}
        </div>

        {/* Divider + User section */}
        <div className="flex items-center gap-2 ml-1 pl-3 border-l border-[var(--border)]">
          {/* Avatar */}
          <div
            className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold shrink-0 select-none"
            title={user?.name}
          >
            {user?.name?.[0]?.toUpperCase() ?? 'U'}
          </div>

          {/* Name + sign out (desktop only) */}
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