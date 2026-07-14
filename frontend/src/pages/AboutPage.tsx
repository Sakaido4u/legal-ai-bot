import { motion } from 'framer-motion'
import { Scale, GitBranch, Mail, ExternalLink } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { APP_NAME, APP_VERSION } from '@/constants/app'

const FEATURES = [
  { emoji: '⚖️', title: 'Compliance Analysis',   desc: 'RAG over GDPR, DPDP, and CCPA sources with citation-bound answers' },
  { emoji: '🔍', title: 'Risk Signals',           desc: 'Heuristic risk flags (lexicon-based) — not a trained legal model' },
  { emoji: '📚', title: 'Grounded Citations',     desc: 'Answers must cite retrieved passages or refuse' },
  { emoji: '📊', title: 'Visual Reports',          desc: 'Charts and compliance scores from your analysis history' },
  { emoji: '🌙', title: 'Dark Mode',               desc: 'Full dark and light mode support' },
  { emoji: '📱', title: 'Responsive Design',       desc: 'Works on mobile, tablet, and desktop' },
]

const ENDPOINTS = [
  { method: 'GET',  path: '/health',                      desc: 'Backend health check'          },
  { method: 'POST', path: '/v1/compliance/analyze',        desc: 'Run compliance analysis'       },
  { method: 'GET',  path: '/v1/compliance/jurisdictions',  desc: 'List available jurisdictions'  },
]

const TECH_STACK = [
  { name: 'React 19',        role: 'UI framework'        },
  { name: 'TypeScript',      role: 'Type safety'         },
  { name: 'Vite',            role: 'Build tool'          },
  { name: 'Tailwind CSS',    role: 'Styling'             },
  { name: 'React Router',    role: 'Client-side routing' },
  { name: 'Axios',           role: 'HTTP client'         },
  { name: 'React Hook Form', role: 'Form management'     },
  { name: 'Zod',             role: 'Schema validation'   },
  { name: 'Framer Motion',   role: 'Animations'          },
  { name: 'Recharts',        role: 'Data visualization'  },
  { name: 'FastAPI',         role: 'Backend REST API'    },
  { name: 'FAISS + Ollama',  role: 'RAG retrieval + LLM' },
]

export function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-8"
      >
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center mx-auto mb-5 shadow-xl shadow-brand-500/25">
          <Scale className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-3xl font-black text-[var(--text)]">{APP_NAME}</h1>
        <p className="text-[var(--text-muted)] mt-2 mb-3">
          Intelligent Legal Research & Compliance Analysis System
        </p>
        <div className="flex items-center justify-center gap-2 flex-wrap">
          <Badge variant="primary">v{APP_VERSION}</Badge>
          <Badge variant="default">React + FastAPI</Badge>
        </div>
      </motion.div>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle>About This Project</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--text-muted)] leading-relaxed">
            LexAI is a college major project: a Retrieval-Augmented Generation (RAG) system
            for cross-jurisdictional compliance research across GDPR, India’s DPDP Act, and
            CCPA/CPRA-related sources. A React frontend talks to a FastAPI backend, which
            retrieves passages from a FAISS index and generates citation-bound answers via
            Ollama (with template/OpenAI fallbacks).
          </p>
          <p className="text-sm text-[var(--text-muted)] leading-relaxed mt-3">
            <strong className="text-[var(--text)]">Academic honesty / scope:</strong> risk
            levels and the compliance score use documented heuristics
            (lexicon factors; score = 100 − peak risk × 100), not a separately trained risk
            model. Outputs are research assist tools — not legal advice — and must be reviewed
            by a qualified person for any real decision.
          </p>
        </CardContent>
      </Card>

      {/* Features */}
      <Card>
        <CardHeader>
          <CardTitle>Key Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="flex items-start gap-3 p-3 rounded-xl bg-[var(--bg-raised)] border border-[var(--border)]"
              >
                <span className="text-xl shrink-0">{f.emoji}</span>
                <div>
                  <p className="text-sm font-semibold text-[var(--text)]">{f.title}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tech stack */}
      <Card>
        <CardHeader>
          <CardTitle>Technology Stack</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {TECH_STACK.map(tech => (
              <div
                key={tech.name}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-[var(--bg-raised)] transition-colors"
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

      {/* API Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle>Backend API Endpoints</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {ENDPOINTS.map(ep => (
            <div
              key={ep.path}
              className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-raised)]"
            >
              <Badge variant={ep.method === 'POST' ? 'warning' : 'primary'}>
                {ep.method}
              </Badge>
              <code className="text-xs font-mono text-[var(--text)] flex-1 truncate">
                {ep.path}
              </code>
              <span className="text-xs text-[var(--text-muted)] shrink-0 hidden sm:block">
                {ep.desc}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Links */}
      <Card>
        <CardHeader>
          <CardTitle>Links & Contact</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border)] text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-raised)] transition-all"
          >
            <GitBranch className="w-4 h-4" />
            GitHub Repository
            <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href="mailto:contact@lexai.com"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border)] text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-raised)] transition-all"
          >
            <Mail className="w-4 h-4" />
            Contact
          </a>
        </CardContent>
      </Card>
    </div>
  )
}