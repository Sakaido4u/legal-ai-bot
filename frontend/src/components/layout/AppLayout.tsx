import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Navbar }  from './Navbar'
import { STORAGE_KEYS } from '@/constants/app'

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() =>
    localStorage.getItem(STORAGE_KEYS.SIDEBAR) === 'true'
  )

  const toggleSidebar = () => {
    setSidebarCollapsed(prev => {
      const next = !prev
      localStorage.setItem(STORAGE_KEYS.SIDEBAR, String(next))
      return next
    })
  }

  return (
    <div className="flex h-screen bg-[var(--bg)] overflow-hidden">
      <Sidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar onMenuClick={toggleSidebar} />

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1400px] mx-auto p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}