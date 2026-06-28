import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { ROUTES } from '@/constants/app'
import {
  LayoutDashboard,
  Search,
  ClipboardList,
  BookOpen,
  Settings,
  Info,
  ChevronLeft,
  Scale,
} from 'lucide-react'

interface NavItem {
  label: string
  path: string
  icon: React.ElementType
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: 'Analyze',   path: ROUTES.ANALYZE,   icon: Search,       badge: 'New' },
  { label: 'Reports',   path: ROUTES.REPORTS,   icon: ClipboardList },
  { label: 'Citations', path: '/citations',      icon: BookOpen },
  { label: 'Settings',  path: ROUTES.SETTINGS,  icon: Settings },
  { label: 'About',     path: ROUTES.ABOUT,      icon: Info },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { pathname } = useLocation()

  return (
    <aside
      className={cn(
        'flex flex-col h-full shrink-0',
        'bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)]',
        'transition-all duration-200 ease-in-out',
        collapsed ? 'w-[60px]' : 'w-[220px]',
      )}
    >
      {/* Logo */}
      <div className="h-14 shrink-0 flex items-center border-b border-[var(--border)] px-3 gap-3 overflow-hidden">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
          <Scale className="w-4 h-4 text-white" />
        </div>
        <span
          className={cn(
            'font-semibold text-sm text-[var(--text)] truncate transition-all duration-200',
            collapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100',
          )}
        >
          LexAI
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const isActive =
            pathname === item.path ||
            (item.path !== '/' && pathname.startsWith(item.path))

          return (
            <Link
              key={item.path}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={cn(
                'relative flex items-center gap-2.5 rounded-lg px-2.5 py-2',
                'text-sm font-medium transition-all duration-100',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-400 nav-item-active'
                  : 'text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)]',
              )}
            >
              <Icon className={cn('shrink-0 transition-all', collapsed ? 'w-5 h-5' : 'w-4 h-4')} />
              {!collapsed && (
                <>
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="text-[0.625rem] font-semibold px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="shrink-0 p-2 border-t border-[var(--border)]">
        <button
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="w-full flex items-center justify-center rounded-lg py-2 gap-2 text-xs text-[var(--text-muted)] hover:bg-[var(--bg-raised)] hover:text-[var(--text)] transition-colors"
        >
          <ChevronLeft
            className={cn('w-4 h-4 transition-transform duration-200', collapsed && 'rotate-180')}
          />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}