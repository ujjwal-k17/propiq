import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Search, Shield, TrendingUp, FileText,
  CheckCircle2, ChevronRight, Star, Globe,
  Building2, Database,
} from 'lucide-react'
import { useCuratedDeals } from '@/hooks'
import {
  SearchBar, ProjectCard, ScoreGauge, ProjectCardSkeleton,
} from '@/components'
import type { CuratedDealsParams } from '@/types'

// ── Page title ────────────────────────────────────────────────────────────────
function usePageTitle(title: string) {
  useEffect(() => { document.title = title }, [title])
}

// ── Mock appreciation data (no chart library needed) ──────────────────────────

// ── Dimension data ────────────────────────────────────────────────────────────
const DIMENSIONS = [
  {
    icon: Shield,
    name: 'Legal & Compliance',
    weight: '25%',
    description: 'RERA registration status, lapse/revocation checks, encumbrance on land.',
    flag: 'Example flag: "RERA registration lapsed 6 months ago"',
    color: 'text-blue-600 bg-blue-50',
  },
  {
    icon: Building2,
    name: 'Developer Track Record',
    weight: '25%',
    description: 'On-time delivery rate, MCA financial stress score, NCLT proceedings.',
    flag: 'Example flag: "Delayed 4 of last 5 projects by 12+ months"',
    color: 'text-propiq-teal bg-teal-50',
  },
  {
    icon: TrendingUp,
    name: 'Project Health',
    weight: '20%',
    description: 'Construction progress, units sold %, revised possession dates.',
    flag: 'Example flag: "Only 12% sold with 3 months to possession"',
    color: 'text-propiq-navy bg-navy-50',
  },
  {
    icon: Globe,
    name: 'Location Quality',
    weight: '15%',
    description: 'Infrastructure, employer proximity, FSI, planned transit connectivity.',
    flag: 'Example flag: "No metro connectivity within 3km"',
    color: 'text-purple-600 bg-purple-50',
  },
  {
    icon: Database,
    name: 'Financial Indicators',
    weight: '10%',
    description: 'Transaction-based price appreciation, rental yield, demand-supply gap.',
    flag: 'Example flag: "Price PSF 40% above market average"',
    color: 'text-amber-600 bg-amber-50',
  },
  {
    icon: TrendingUp,
    name: 'Macro Environment',
    weight: '5%',
    description: 'GDP growth trajectory, RBI rate outlook, NRI demand index.',
    flag: 'Example flag: "Rate hike cycle may impact affordability"',
    color: 'text-slate-600 bg-slate-100',
  },
]

const TESTIMONIALS = [
  {
    name: 'Rajeev Menon',
    role: 'NRI investor, Dubai',
    avatar: 'RM',
    text: 'PropIQ saved me from investing ₹1.8Cr in a project where the developer had an active NCLT case. The risk report was clear, detailed, and backed by real data.',
    rating: 5,
  },
  {
    name: 'Priya Krishnaswamy',
    role: 'First-time buyer, Bengaluru',
    avatar: 'PK',
    text: "I was relying on the builder's sales team until PropIQ showed me 18 RERA complaints against the same developer. Changed my decision entirely.",
    rating: 5,
  },
  {
    name: 'Amit Sharma',
    role: 'Portfolio investor, Mumbai',
    avatar: 'AS',
    text: 'The 3-year appreciation forecast with bull/base/bear cases is exactly what I needed to compare 3 projects in Thane. Professional-grade analysis in minutes.',
    rating: 5,
  },
]

const DATA_SOURCES = ['RERA Portals', 'MCA21', 'eCourts', 'News APIs', 'Transaction Registry']

const CITIES = ['Mumbai', 'Bengaluru', 'Pune', 'Hyderabad', 'Delhi NCR']

export function HomePage() {
  usePageTitle('PropIQ — Real Estate Due Diligence for India')
  const heroSearchRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const [activeCity, setActiveCity] = useState<string | undefined>(undefined)

  const curatedParams: CuratedDealsParams = { city: activeCity, limit: 6 }
  const { data: curatedDeals = [], isLoading: dealsLoading } = useCuratedDeals(curatedParams)

  return (
    <div className="overflow-x-hidden">
      {/* ── 1. HERO ──────────────────────────────────────────────────────── */}
      <section className="relative bg-propiq-gradient overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full bg-propiq-teal blur-3xl" />
        </div>

        <div className="relative max-w-4xl mx-auto px-4 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 bg-white/15 border border-white/25 rounded-full px-4 py-1.5 text-white/90 text-sm font-medium mb-8">
            <Shield size={13} />
            AI-Powered Real Estate Due Diligence
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-white mb-5 leading-tight">
            Know before you invest.
            <br />
            <span className="text-teal-300">Real estate due diligence</span>
            <br />
            for India.
          </h1>

          <p className="text-lg sm:text-xl text-white/75 mb-10 max-w-2xl mx-auto leading-relaxed">
            PropIQ analyzes 6 risk dimensions across legal, developer, construction, location,
            and financial factors — so you don't have to rely on a broker's word.
          </p>

          {/* Search */}
          <div ref={heroSearchRef} className="max-w-2xl mx-auto mb-6">
            <SearchBar
              size="lg"
              placeholder="Search by project name, developer, or RERA ID..."
              className="shadow-2xl"
            />
          </div>

          {/* Quick city pills */}
          <div className="flex flex-wrap justify-center gap-2 mb-10">
            {CITIES.map((city) => (
              <button
                key={city}
                onClick={() => navigate(`/search?q=${city}`)}
                className="px-4 py-1.5 bg-white/15 hover:bg-white/25 border border-white/20 text-white/90 text-sm rounded-full transition-colors"
              >
                {city}
              </button>
            ))}
          </div>

          {/* Trust indicators */}
          <div className="flex flex-wrap justify-center gap-6 text-white/70 text-sm">
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-teal-300" /> 10,000+ projects analyzed</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-teal-300" /> Trusted by NRI investors</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 size={14} className="text-teal-300" /> Live RERA data</span>
          </div>
        </div>
      </section>

      {/* ── 2. HOW IT WORKS ─────────────────────────────────────────────── */}
      <section className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <p className="text-propiq-teal font-semibold text-sm uppercase tracking-wide mb-2">Simple process</p>
            <h2 className="text-3xl font-bold text-propiq-navy">How PropIQ works</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                icon: Search,
                title: 'Search any project or developer',
                desc: 'Type a project name, RERA number, or developer. PropIQ searches across all registered projects in India.',
              },
              {
                step: '02',
                icon: Shield,
                title: 'Get AI-powered risk score',
                desc: 'Our engine scores 6 dimensions — legal, developer, construction, location, financial, macro — weighted by impact.',
              },
              {
                step: '03',
                icon: FileText,
                title: 'Read the full diligence report',
                desc: 'Download a PDF report with every flag, data source, and appreciation forecast before you sign anything.',
              },
            ].map(({ step, icon: Icon, title, desc }) => (
              <div key={step} className="text-center">
                <div className="relative inline-flex mb-5">
                  <div className="w-16 h-16 rounded-2xl bg-navy-50 flex items-center justify-center">
                    <Icon size={26} className="text-propiq-navy" />
                  </div>
                  <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-propiq-teal text-white text-xs font-bold flex items-center justify-center">
                    {step.slice(1)}
                  </span>
                </div>
                <h3 className="font-bold text-propiq-navy text-lg mb-2">{title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. CURATED OPPORTUNITIES ────────────────────────────────────── */}
      <section className="py-20 bg-surface">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex items-center justify-between mb-8">
            <div>
              <p className="text-propiq-teal font-semibold text-sm uppercase tracking-wide mb-1">Curated by PropIQ</p>
              <h2 className="text-2xl font-bold text-propiq-navy">Top-rated projects right now</h2>
            </div>
            <Link
              to="/discover"
              className="hidden sm:flex items-center gap-1 text-sm font-medium text-propiq-blue hover:text-propiq-navy transition-colors"
            >
              View all <ChevronRight size={14} />
            </Link>
          </div>

          {/* City tabs */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {[undefined, ...CITIES].map((city) => (
              <button
                key={city ?? 'all'}
                onClick={() => setActiveCity(city)}
                className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  activeCity === city
                    ? 'bg-propiq-navy text-white border-propiq-navy'
                    : 'border-slate-200 text-slate-600 hover:border-propiq-blue'
                }`}
              >
                {city ?? 'All India'}
              </button>
            ))}
          </div>

          {/* Grid */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {dealsLoading
              ? Array.from({ length: 6 }).map((_, i) => <ProjectCardSkeleton key={i} />)
              : curatedDeals.slice(0, 6).map((deal) => (
                  <ProjectCard
                    key={deal.project.id}
                    project={deal.project}
                    riskScore={deal.risk_score}
                  />
                ))}
            {!dealsLoading && curatedDeals.length === 0 && (
              <div className="col-span-3 text-center py-16 text-slate-400">
                No curated deals available for this filter. Try a different city.
              </div>
            )}
          </div>

          <div className="text-center mt-8 sm:hidden">
            <Link to="/discover" className="text-sm font-medium text-propiq-blue hover:underline">
              View all projects →
            </Link>
          </div>
        </div>
      </section>

      {/* ── 4. RISK SCORE EXPLAINER ──────────────────────────────────────── */}
      <section className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-propiq-teal font-semibold text-sm uppercase tracking-wide mb-2">How we score</p>
              <h2 className="text-2xl font-bold text-propiq-navy mb-3">6 dimensions. One score.</h2>
              <p className="text-slate-500 mb-8 leading-relaxed">
                PropIQ's algorithm evaluates projects across 6 risk dimensions, each weighted by
                its impact on investment safety. A score of 80+ is Low Risk; below 40 is Critical.
              </p>
              <div className="flex justify-center">
                <ScoreGauge score={74} size={180} label="Sample PropIQ Score" />
              </div>
            </div>

            <div className="space-y-3">
              {DIMENSIONS.map(({ icon: Icon, name, weight, description, flag, color }) => (
                <div key={name} className="flex gap-3 p-3 rounded-xl hover:bg-slate-50 transition-colors">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="font-semibold text-sm text-propiq-navy">{name}</p>
                      <span className="text-2xs text-slate-400 font-mono">{weight}</span>
                    </div>
                    <p className="text-xs text-slate-500 leading-snug">{description}</p>
                    <p className="text-2xs text-risk-medium mt-1 italic">{flag}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. TESTIMONIALS ─────────────────────────────────────────────── */}
      <section className="py-20 bg-surface">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-propiq-navy">Trusted by smart investors</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="bg-white rounded-2xl p-6 shadow-card">
                <div className="flex gap-0.5 mb-4">
                  {Array.from({ length: t.rating }).map((_, i) => (
                    <Star key={i} size={14} className="text-amber-400 fill-amber-400" />
                  ))}
                </div>
                <p className="text-sm text-slate-600 leading-relaxed mb-4 italic">"{t.text}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-propiq-gradient flex items-center justify-center text-white text-xs font-bold font-mono">
                    {t.avatar}
                  </div>
                  <div>
                    <p className="font-semibold text-sm text-propiq-navy">{t.name}</p>
                    <p className="text-xs text-slate-400">{t.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Data sources */}
          <div className="text-center">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-4">Powered by data from</p>
            <div className="flex flex-wrap justify-center gap-4">
              {DATA_SOURCES.map((s) => (
                <span key={s} className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-500 shadow-sm">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 6. CTA ───────────────────────────────────────────────────────── */}
      <section className="py-20 bg-propiq-gradient">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Start your free due diligence report
          </h2>
          <p className="text-white/70 mb-8">
            Search any RERA-registered project. No credit card required.
          </p>
          <button
            onClick={() => heroSearchRef.current?.querySelector('input')?.focus()}
            className="inline-flex items-center gap-2 bg-white text-propiq-navy font-bold px-8 py-4 rounded-xl hover:bg-navy-50 transition-colors shadow-xl text-base"
          >
            <Search size={18} /> Search a project
          </button>
        </div>
      </section>
    </div>
  )
}
