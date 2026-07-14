import { useCallback, useEffect, useState } from 'react'
import { Shield, Trash2, UserX, UserCheck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { adminService } from '@/services/adminService'
import { useAuth } from '@/context/AuthContext'
import { formatDate } from '@/utils/formatters'
import type { AdminUser } from '@/types/auth'
import toast from 'react-hot-toast'

export function AdminPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await adminService.listUsers()
      setUsers(data.users)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load users'
      toast.error(message)
      setUsers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (!user?.is_admin) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-[var(--text-muted)]">
          Admin access required.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text)] flex items-center gap-2">
          <Shield className="w-6 h-6 text-brand-600" />
          User admin
        </h1>
        <p className="text-sm text-[var(--text-muted)] mt-1">
          List, deactivate, or delete accounts without touching the database.
        </p>
      </div>

      <Card padding="none">
        <CardHeader className="border-b border-[var(--border)]">
          <CardTitle>Users ({users.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-6 text-sm text-[var(--text-muted)]">Loading…</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-[var(--bg-raised)] border-b border-[var(--border)]">
                    {['Name', 'Email', 'Role', 'Status', 'Created', 'Actions'].map(h => (
                      <th
                        key={h}
                        className="px-5 py-2.5 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {users.map(row => (
                    <tr key={row.id} className="hover:bg-[var(--bg-raised)]">
                      <td className="px-5 py-3.5 text-sm font-medium text-[var(--text)]">
                        {row.name}
                      </td>
                      <td className="px-5 py-3.5 text-sm text-[var(--text-muted)]">
                        {row.email}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={row.is_admin ? 'default' : 'outline'}>
                          {row.is_admin ? 'Admin' : 'User'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={row.is_active ? 'success' : 'danger'}>
                          {row.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-xs text-[var(--text-muted)]">
                        {row.created_at ? formatDate(row.created_at) : '—'}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-1">
                          {row.is_active ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Deactivate"
                              disabled={row.id === user.id}
                              onClick={async () => {
                                try {
                                  await adminService.deactivate(row.id)
                                  toast.success('User deactivated')
                                  await load()
                                } catch (err: unknown) {
                                  toast.error(err instanceof Error ? err.message : 'Failed')
                                }
                              }}
                            >
                              <UserX className="w-4 h-4" />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Activate"
                              onClick={async () => {
                                try {
                                  await adminService.activate(row.id)
                                  toast.success('User activated')
                                  await load()
                                } catch (err: unknown) {
                                  toast.error(err instanceof Error ? err.message : 'Failed')
                                }
                              }}
                            >
                              <UserCheck className="w-4 h-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Delete"
                            disabled={row.id === user.id}
                            onClick={async () => {
                              if (!window.confirm(`Delete ${row.email}?`)) return
                              try {
                                await adminService.deleteUser(row.id)
                                toast.success('User deleted')
                                await load()
                              } catch (err: unknown) {
                                toast.error(err instanceof Error ? err.message : 'Failed')
                              }
                            }}
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
