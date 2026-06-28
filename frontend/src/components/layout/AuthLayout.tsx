import { Outlet, Link } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { APP_NAME, APP_TAGLINE } from '@/constants/app'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-[var(--bg)] flex">

      {/* Left branding panel — hidden on mobile */}
      <div className="hidden lg:flex lg:w-[45%] bg-brand-900 flex-col justify-between p-10 relative overflow-hidden">
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px),' +
              'linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        {/* Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-brand-700/30 blur-3xl pointer-events-none" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-600 flex items-center justify-center">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <span className="text-white font-semibold text-lg">{APP_NAME}</span>
        </div>

        {/* Bottom text */}
        <div className="relative z-10 space-y-4">
          <p className="text-2xl font-semibold text-white leading-relaxed">
            "Legal intelligence,
            <br />
            <span className="text-brand-300">powered by AI."</span>
          </p>
          <p className="text-brand-400 text-sm">{APP_TAGLINE}</p>
          <div className="space-y-2 pt-2">
            {[
              'Analyze compliance across 15 jurisdictions',
              'Smart citations with section references',
              'Risk detection with confidence scores',
            ].map(item => (
              <div key={item} className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                <span className="text-brand-300 text-sm">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex flex-col min-h-screen">
        <div className="flex items-center justify-between p-5 shrink-0">
          <Link to="/" className="flex items-center gap-2 lg:invisible">
            <div className="w-7 h-7 rounded-md bg-brand-600 flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-[var(--text)] text-sm">{APP_NAME}</span>
          </Link>
          <ThemeToggle size="sm" />
        </div>

        <div className="flex-1 flex items-center justify-center px-6 pb-10">
          <div className="w-full max-w-[400px]">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  )
}