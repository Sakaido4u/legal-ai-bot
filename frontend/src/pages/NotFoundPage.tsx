import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, ArrowLeft, Scale } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ROUTES } from '@/constants/app'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[var(--bg)] flex flex-col items-center justify-center p-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-md w-full"
      >
        {/* Logo */}
        <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto mb-6">
          <Scale className="w-7 h-7 text-white" />
        </div>

        {/* 404 */}
        <motion.p
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="text-[120px] sm:text-[160px] font-black text-[var(--border)] leading-none select-none"
        >
          404
        </motion.p>

        <h1 className="text-2xl font-bold text-[var(--text)] mt-2 mb-2">
          Page not found
        </h1>
        <p className="text-[var(--text-muted)] mb-8 leading-relaxed">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
          Check the URL or navigate back to safety.
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            variant="outline"
            onClick={() => navigate(-1)}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Go back
          </Button>
          <Link to={ROUTES.HOME}>
            <Button leftIcon={<Home className="w-4 h-4" />}>
              Go to Home
            </Button>
          </Link>
        </div>

        {/* Quick links */}
        <div className="mt-8 pt-6 border-t border-[var(--border)]">
          <p className="text-xs text-[var(--text-subtle)] mb-3">Quick links</p>
          <div className="flex items-center justify-center gap-4 text-sm">
            <Link to={ROUTES.DASHBOARD} className="text-brand-600 hover:underline">Dashboard</Link>
            <Link to={ROUTES.ANALYZE}   className="text-brand-600 hover:underline">Analyze</Link>
            <Link to={ROUTES.REPORTS}   className="text-brand-600 hover:underline">Reports</Link>
            <Link to={ROUTES.SETTINGS}  className="text-brand-600 hover:underline">Settings</Link>
          </div>
        </div>
      </motion.div>
    </div>
  )
}