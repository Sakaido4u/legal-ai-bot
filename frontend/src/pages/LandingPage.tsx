import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Scale, Shield, Search, BookOpen,
  ArrowRight, CheckCircle, Zap, Globe,
  ChevronRight,
} from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { ROUTES } from '@/constants/app'

const FEATURES = [
  {
    icon:  Search,
    title: 'Compliance Analysis',
    desc:  'Analyze any legal query against multiple jurisdictions instantly.',
    color: 'text-blue-500',
    bg:    'bg-blue-50 dark:bg-blue-950/40',
  },
  {
    icon:  Shield,
    title: 'Risk Detection',
    desc:  'Identify high, medium, and low risk areas with confidence scores.',
    color: 'text-amber-500',
    bg:    'bg-amber-50 dark:bg-amber-950/40',
  },
  {
    icon:  BookOpen,
    title: 'Smart Citations',
    desc:  'Every recommendation backed by exact legal citations and section references.',
    color: 'text-green-500',
    bg:    'bg-green-50 dark:bg-green-950/40',
  },
  {
    icon:  Globe,
    title: 'Multi-Jurisdiction',
    desc:  'Full coverage across Indian, US, EU, and UK legal frameworks.',
    color: 'text-purple-500',
    bg:    'bg-purple-50 dark:bg-purple-950/40',
  },
  {
    icon:  Zap,
    title: 'Instant Results',
    desc:  'Comprehensive compliance reports delivered in under 10 seconds.',
    color: 'text-rose-500',
    bg:    'bg-rose-50 dark:bg-rose-950/40',
  },
  {
    icon:  CheckCircle,
    title: 'Export Ready',
    desc:  'Download professional PDF reports for clients and stakeholders.',
    color: 'text-teal-500',
    bg:    'bg-teal-50 dark:bg-teal-950/40',
  },
]

const STATS = [
  { value: '500+', label: 'Laws Indexed'   },
  { value: '15',   label: 'Jurisdictions'  },
  { value: '99%',  label: 'Accuracy Rate'  },
  { value: '<10s', label: 'Avg Response'   },
]

const STEPS = [
  {
    n:     '01',
    title: 'Describe your query',
    desc:  'Enter any legal question, clause, or compliance concern in plain English.',
  },
  {
    n:     '02',
    title: 'Select jurisdiction',
    desc:  'Choose from 15+ legal jurisdictions across India, US, EU, and UK.',
  },
  {
    n:     '03',
    title: 'Get instant analysis',
    desc:  'Receive a full compliance report with risk levels and citations in seconds.',
  },
]

const fadeUp = {
  hidden:  { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity:    1,
    y:          0,
    transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' },
  }),
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)]">

      {/* ── Fixed Navbar ──────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg)]/80 backdrop-blur-md border-b border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-[var(--text)]">LexAI</span>
          </Link>

          <div className="flex items-center gap-2">
            <ThemeToggle size="sm" />
            <Link
              to={ROUTES.LOGIN}
              className="px-3 py-1.5 rounded-lg text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-raised)] transition-all"
            >
              Log in
            </Link>
            <Link
              to={ROUTES.REGISTER}
              className="px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-600 text-white hover:bg-brand-700 transition-colors shadow-sm"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────── */}
      <section className="relative pt-28 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-brand-50/80 via-[var(--bg)] to-[var(--bg)] dark:from-brand-950/20 dark:via-[var(--bg)] pointer-events-none" />
        <div
          className="absolute inset-0 opacity-40 dark:opacity-20 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle, #CBD5E1 1px, transparent 1px)',
            backgroundSize:  '28px 28px',
          }}
        />

        <div className="relative max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300 border border-brand-200 dark:border-brand-800 mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
              AI-Powered Legal Research
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.08 }}
            className="text-5xl sm:text-6xl font-extrabold text-[var(--text)] leading-tight mb-5"
          >
            Legal Intelligence,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-brand-400">
              Powered by AI.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.16 }}
            className="text-lg text-[var(--text-muted)] mb-8 max-w-2xl mx-auto leading-relaxed"
          >
            Analyze compliance, identify legal risks, and get smart citations
            across 15+ jurisdictions — all in under 10 seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.24 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            <Link
              to={ROUTES.REGISTER}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-lg shadow-brand-600/25"
            >
              Start for Free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to={ROUTES.LOGIN}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-[var(--border)] text-[var(--text)] font-medium hover:bg-[var(--bg-raised)] transition-colors"
            >
              Sign In <ChevronRight className="w-4 h-4" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ── Stats bar ─────────────────────────────────────── */}
      <section className="border-y border-[var(--border)] bg-[var(--bg-surface)] py-10">
        <div className="max-w-4xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.07 }}
                className="text-center"
              >
                <p className="text-3xl font-black text-brand-600">{stat.value}</p>
                <p className="text-sm text-[var(--text-muted)] mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2">
              How it works
            </p>
            <h2 className="text-3xl font-bold text-[var(--text)]">
              Three steps to legal clarity
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.n}
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                className="relative p-6 rounded-2xl border border-[var(--border)] bg-[var(--bg-surface)] hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
              >
                <span className="text-4xl font-black text-[var(--border)] leading-none">
                  {step.n}
                </span>
                <h3 className="font-semibold text-[var(--text)] mt-3 mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                  {step.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────── */}
      <section className="py-20 px-6 bg-[var(--bg-surface)] border-y border-[var(--border)]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-xs font-bold text-brand-600 uppercase tracking-widest mb-2">
              Features
            </p>
            <h2 className="text-3xl font-bold text-[var(--text)] mb-3">
              Everything you need for legal compliance
            </h2>
            <p className="text-[var(--text-muted)] max-w-xl mx-auto">
              Built for legal professionals, compliance officers, and developers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((feat, i) => {
              const Icon = feat.icon
              return (
                <motion.div
                  key={feat.title}
                  custom={i}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true }}
                  variants={fadeUp}
                  className="group p-5 rounded-2xl border border-[var(--border)] bg-[var(--bg)] hover:border-[var(--border-strong)] hover:shadow-md transition-all duration-200"
                >
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-200', feat.bg)}>
                    <Icon className={cn('w-5 h-5', feat.color)} />
                  </div>
                  <h3 className="font-semibold text-[var(--text)] mb-1.5">
                    {feat.title}
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                    {feat.desc}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 p-12 text-center shadow-2xl">
            <div
              className="absolute inset-0 opacity-10"
              style={{
                backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
                backgroundSize:  '24px 24px',
              }}
            />
            <div className="relative z-10">
              <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
                Start analyzing legal documents today
              </h2>
              <p className="text-brand-200 mb-8 text-sm sm:text-base">
                Join teams using LexAI for faster, more accurate compliance analysis.
              </p>
              <Link
                to={ROUTES.REGISTER}
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-white text-brand-700 font-semibold hover:bg-brand-50 transition-colors shadow-lg"
              >
                Create free account <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="border-t border-[var(--border)] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-brand-600 flex items-center justify-center">
              <Scale className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold text-[var(--text)]">LexAI</span>
          </div>
          <p className="text-xs text-[var(--text-subtle)] text-center">
            Intelligent Legal Research & Compliance Analysis
          </p>
          <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
            <Link to={ROUTES.ABOUT} className="hover:text-[var(--text)] transition-colors">
              About
            </Link>
            <Link to={ROUTES.LOGIN} className="hover:text-[var(--text)] transition-colors">
              Login
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

// ── Helper (used inside LandingPage only) ──────────────────────
function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}