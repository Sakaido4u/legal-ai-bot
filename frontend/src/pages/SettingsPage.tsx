import { useState } from 'react'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  User, Palette, Bell, Activity,
  Info, CheckCircle, XCircle,
  Loader2, Save, Scale,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button }      from '@/components/ui/Button'
import { Input }       from '@/components/ui/Input'
import { Badge }       from '@/components/ui/Badge'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuth }     from '@/context/AuthContext'
import { useTheme }    from '@/context/ThemeContext'
import { useHealth }   from '@/hooks/useHealth'
import { cn }          from '@/utils/cn'
import toast           from 'react-hot-toast'
import { APP_NAME, APP_VERSION } from '@/constants/app'

// ── Tabs ───────────────────────────────────────────────────────
const TABS = [
  { id: 'profile',       label: 'Profile',       icon: User     },
  { id: 'appearance',    label: 'Appearance',    icon: Palette  },
  { id: 'notifications', label: 'Notifications', icon: Bell     },
  { id: 'api',           label: 'API Status',    icon: Activity },
  { id: 'about',         label: 'About',         icon: Info     },
] as const

type TabId = typeof TABS[number]['id']

// ── Profile form schema ────────────────────────────────────────
const profileSchema = z.object({
  name:  z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Enter a valid email'),
})
type ProfileFormData = z.infer<typeof profileSchema>

// ── Profile Tab ────────────────────────────────────────────────
function ProfileTab() {
  const { user, updateUser } = useAuth()

  const { register, handleSubmit, formState: { errors, isSubmitting, isDirty } } =
    useForm<ProfileFormData>({
      resolver: zodResolver(profileSchema),
      defaultValues: {
        name:  user?.name  ?? '',
        email: user?.email ?? '',
      },
    })

  const onSubmit = async (data: ProfileFormData) => {
    // Local profile display only — preserves the real JWT (no backend profile API yet).
    if (user) {
      updateUser({ ...user, name: data.name, email: data.email })
    }
    toast.success('Profile updated locally')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profile Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Avatar */}
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {user?.name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div>
            <p className="font-semibold text-[var(--text)]">{user?.name}</p>
            <p className="text-sm text-[var(--text-muted)]">{user?.email}</p>
            <Badge variant="success" className="mt-1">
              <CheckCircle className="w-3 h-3" />
              Active
            </Badge>
          </div>
        </div>

        <hr className="border-[var(--border)]" />

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Full Name"
            placeholder="Your full name"
            error={errors.name?.message}
            {...register('name')}
          />
          <Input
            label="Email Address"
            type="email"
            placeholder="your@email.com"
            error={errors.email?.message}
            {...register('email')}
          />
          <Button
            type="submit"
            isLoading={isSubmitting}
            disabled={!isDirty}
            leftIcon={<Save className="w-4 h-4" />}
          >
            Save Changes
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

// ── Appearance Tab ─────────────────────────────────────────────
function AppearanceTab() {
  const { theme, setTheme, isDark } = useTheme()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-[var(--text)]">Theme</p>
            <p className="text-sm text-[var(--text-muted)] mt-0.5">
              Currently: {isDark ? 'Dark' : 'Light'} mode
            </p>
          </div>
          <ThemeToggle />
        </div>

        <hr className="border-[var(--border)]" />

        {/* Theme presets */}
        <div>
          <p className="text-sm font-medium text-[var(--text)] mb-3">
            Quick select
          </p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Light',  value: 'light' as const, preview: 'bg-white border-gray-200'   },
              { label: 'Dark',   value: 'dark'  as const, preview: 'bg-gray-900 border-gray-700' },
            ].map(t => (
              <button
                key={t.value}
                onClick={() => setTheme(t.value)}
                className={cn(
                  'relative p-4 rounded-xl border-2 transition-all text-left',
                  theme === t.value
                    ? 'border-brand-500 shadow-md shadow-brand-500/10'
                    : 'border-[var(--border)] hover:border-[var(--border-strong)]',
                )}
              >
                <div className={cn('w-full h-12 rounded-lg mb-3 border', t.preview)} />
                <p className="text-sm font-medium text-[var(--text)]">{t.label}</p>
                {theme === t.value && (
                  <CheckCircle className="absolute top-2 right-2 w-4 h-4 text-brand-500" />
                )}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Notifications Tab ──────────────────────────────────────────
function NotificationsTab() {
  const [settings, setSettings] = useState({
    analysisComplete: true,
    highRiskAlert:    true,
    weeklyReport:     false,
    systemUpdates:    true,
  })

  const toggle = (key: keyof typeof settings) => {
    setSettings(p => ({ ...p, [key]: !p[key] }))
    toast.success('Notification preference saved')
  }

  const NOTIF_ITEMS = [
    { key: 'analysisComplete' as const, label: 'Analysis complete',  desc: 'Notify when a compliance analysis finishes'    },
    { key: 'highRiskAlert'    as const, label: 'High risk alerts',   desc: 'Alert when high-risk items are detected'       },
    { key: 'weeklyReport'     as const, label: 'Weekly summary',     desc: 'Receive a weekly report of your analyses'      },
    { key: 'systemUpdates'    as const, label: 'System updates',     desc: 'Get notified about new features and changes'   },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notifications</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-[var(--border)]">
          {NOTIF_ITEMS.map(item => (
            <div key={item.key} className="flex items-center justify-between py-4">
              <div>
                <p className="text-sm font-medium text-[var(--text)]">{item.label}</p>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">{item.desc}</p>
              </div>
              {/* Toggle switch */}
              <button
                onClick={() => toggle(item.key)}
                className={cn(
                  'relative w-11 h-6 rounded-full transition-all duration-200',
                  settings[item.key] ? 'bg-brand-600' : 'bg-[var(--border)]',
                )}
                role="switch"
                aria-checked={settings[item.key]}
              >
                <span
                  className={cn(
                    'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200',
                    settings[item.key] && 'translate-x-5',
                  )}
                />
              </button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// ── API Status Tab ─────────────────────────────────────────────
function ApiStatusTab() {
  const { status, details, lastCheck, check } = useHealth()

  const STATUS_CONFIG = {
    idle:        { color: 'text-[var(--text-muted)]',  bg: 'bg-[var(--bg-raised)]', label: 'Not checked' },
    checking:    { color: 'text-brand-600',             bg: 'bg-brand-50 dark:bg-brand-900/20', label: 'Checking…' },
    healthy:     { color: 'text-green-600',             bg: 'bg-green-50 dark:bg-green-900/20', label: 'Healthy'   },
    degraded:    { color: 'text-amber-600',             bg: 'bg-amber-50 dark:bg-amber-900/20', label: 'Degraded'  },
    unreachable: { color: 'text-red-600',               bg: 'bg-red-50 dark:bg-red-900/20',     label: 'Unreachable' },
  }

  const cfg = STATUS_CONFIG[status]

  const ENDPOINTS = [
    { method: 'GET',  path: '/health',                      desc: 'Health check'       },
    { method: 'POST', path: '/auth/login',                   desc: 'Login'              },
    { method: 'POST', path: '/documents/upload',             desc: 'Upload PDF'         },
    { method: 'POST', path: '/v1/compliance/analyze',        desc: 'Run analysis'       },
    { method: 'GET',  path: '/v1/compliance/jurisdictions',  desc: 'List jurisdictions' },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Status indicator */}
        <div className={cn('flex items-center justify-between p-4 rounded-xl border', cfg.bg,
          status === 'healthy' ? 'border-green-200 dark:border-green-900/40'
          : status === 'unreachable' ? 'border-red-200 dark:border-red-900/40'
          : 'border-[var(--border)]')}>
          <div className="flex items-center gap-3">
            {status === 'checking' ? (
              <Loader2 className="w-5 h-5 text-brand-600 animate-spin" />
            ) : status === 'healthy' ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : status === 'unreachable' ? (
              <XCircle className="w-5 h-5 text-red-600" />
            ) : (
              <Activity className="w-5 h-5 text-[var(--text-muted)]" />
            )}
            <div>
              <p className={cn('font-semibold text-sm', cfg.color)}>{cfg.label}</p>
              {details && (
                <p className="text-xs text-[var(--text-muted)] mt-0.5">
                  {details.version ? `v${details.version}` : 'API'}
                  {typeof details.index_vectors === 'number'
                    ? ` · Index: ${details.index_vectors}`
                    : ''}
                  {details.llm_provider ? ` · LLM: ${details.llm_provider}` : ''}
                  {typeof details.uptime_seconds === 'number' && details.uptime_seconds > 0
                    ? ` · Uptime: ${Math.floor(details.uptime_seconds / 60)}m`
                    : ''}
                </p>
              )}
              {lastCheck && (
                <p className="text-xs text-[var(--text-subtle)] mt-0.5">
                  Last checked: {lastCheck.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void check()}
            isLoading={status === 'checking'}
          >
            Check now
          </Button>
        </div>

        {/* Endpoints */}
        <div>
          <p className="text-sm font-semibold text-[var(--text)] mb-3">
            Backend Endpoints
          </p>
          <div className="space-y-2">
            {ENDPOINTS.map(ep => (
              <div
                key={ep.path}
                className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)]"
              >
                <Badge variant={ep.method === 'POST' ? 'warning' : 'primary'}>
                  {ep.method}
                </Badge>
                <code className="text-xs font-mono text-[var(--text)] flex-1">
                  {ep.path}
                </code>
                <span className="text-xs text-[var(--text-muted)]">{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── About Tab ──────────────────────────────────────────────────
function AboutTab() {
  const TECH_STACK = [
    { name: 'React 18',           role: 'UI framework'         },
    { name: 'TypeScript',         role: 'Type safety'          },
    { name: 'Vite',               role: 'Build tool'           },
    { name: 'Tailwind CSS',       role: 'Styling'              },
    { name: 'React Router v6',    role: 'Client-side routing'  },
    { name: 'Axios',              role: 'HTTP client'          },
    { name: 'React Hook Form',    role: 'Form management'      },
    { name: 'Zod',                role: 'Schema validation'    },
    { name: 'Framer Motion',      role: 'Animations'           },
    { name: 'Recharts',           role: 'Data visualization'   },
    { name: 'FastAPI (backend)',   role: 'REST API server'      },
  ]

  return (
    <div className="space-y-5">
      <Card>
        <CardContent className="pt-5">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center shrink-0">
              <Scale className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[var(--text)]">{APP_NAME}</h2>
              <p className="text-sm text-[var(--text-muted)]">
                Intelligent Legal Research & Compliance Analysis
              </p>
              <Badge variant="default" className="mt-1">v{APP_VERSION}</Badge>
            </div>
          </div>
          <p className="text-sm text-[var(--text-muted)] leading-relaxed">
            LexAI is a Final Year Project that demonstrates AI-powered legal compliance analysis.
            It analyzes legal queries against multiple jurisdictions, identifies risks, provides
            citations, and generates actionable recommendations.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Technology Stack</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {TECH_STACK.map(tech => (
              <div
                key={tech.name}
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-[var(--bg-raised)] transition-colors"
              >
                <span className="text-sm font-medium text-[var(--text)]">
                  {tech.name}
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {tech.role}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ── Main Component ──────────────────────────────────────────────
export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  const TAB_CONTENT: Record<TabId, React.ReactNode> = {
    profile:       <ProfileTab />,
    appearance:    <AppearanceTab />,
    notifications: <NotificationsTab />,
    api:           <ApiStatusTab />,
    about:         <AboutTab />,
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text)]">Settings</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">
          Manage your account and application preferences.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--bg-raised)] rounded-xl overflow-x-auto">
        {TABS.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-150',
                activeTab === tab.id
                  ? 'bg-[var(--bg-surface)] text-[var(--text)] shadow-sm'
                  : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-surface)]/50',
              )}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {TAB_CONTENT[activeTab]}
      </motion.div>
    </div>
  )
}