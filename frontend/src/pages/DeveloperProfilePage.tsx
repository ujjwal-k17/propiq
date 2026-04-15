import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Building2, MapPin, Calendar, AlertTriangle, CheckCircle2,
  TrendingUp, Users, Clock, MessageSquare, ExternalLink,
} from 'lucide-react'
import { getDeveloperDetail, getDeveloperProjects } from '@/services/api'
import {
  ScoreGauge, ProjectListItem, Button,
} from '@/components'
import type { Developer, ProjectSummary, RiskScoreBrief } from '@/types'
import { getRiskColor } from '@/utils/formatters'

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({
  label, value, icon: Icon, color = 'text-propiq-navy',
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color?: string
}) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-card">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <Icon size={16} className={color} />
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-6">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-24 bg-slate-100 rounded-2xl animate-pulse" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type Tab = 'projects' | 'complaints' | 'news'

export function DeveloperProfilePage() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('projects')

  const { data: devRaw, isLoading, isError } = useQuery<Record<string, unknown>>({
    queryKey: ['developer', id],
    queryFn: () => getDeveloperDetail(id!),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })

  const { data: projectsData } = useQuery({
    queryKey: ['developer-projects', id],
    queryFn: () => getDeveloperProjects(id!, { limit: 20 }),
    enabled: !!id && tab === 'projects',
    staleTime: 5 * 60 * 1000,
  })

  const dev = devRaw as Developer | undefined

  useEffect(() => {
    if (dev?.name) document.title = `${dev.name} — PropIQ`
    else document.title = 'Developer Profile — PropIQ'
  }, [dev?.name])

  if (isLoading) return <LoadingState />

  if (isError || !dev) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-slate-500 mb-4">Developer not found or failed to load.</p>
        <Link to="/search" className="text-propiq-blue hover:underline text-sm">← Back to search</Link>
      </div>
    )
  }

  const onTimePct = dev.projects_on_time_pct ?? 0
  const stressScore = dev.financial_stress_score ?? null

  // Stats
  const delivered = dev.total_projects_delivered ?? 0
  const complaints = dev.active_complaint_count ?? 0
  const totalUnits = (dev as Record<string, unknown>).total_units_delivered as number | undefined

  const tabs: { id: Tab; label: string }[] = [
    { id: 'projects', label: 'Projects' },
    { id: 'complaints', label: `Complaints${complaints > 0 ? ` (${complaints})` : ''}` },
    { id: 'news', label: 'News & Alerts' },
  ]

  const projects = (projectsData?.items ?? []) as ProjectSummary[]

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* ── Header ── */}
      <div className="bg-white rounded-3xl shadow-card p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-5">
          {/* Avatar */}
          <div className="w-16 h-16 rounded-2xl bg-propiq-gradient flex items-center justify-center text-white text-xl font-bold shrink-0">
            {dev.name.charAt(0).toUpperCase()}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h1 className="text-xl font-extrabold text-propiq-navy">{dev.name}</h1>
              {dev.nclt_proceedings && (
                <span className="flex items-center gap-1 text-xs font-bold bg-red-50 text-red-600 border border-red-200 rounded-full px-2 py-0.5">
                  <AlertTriangle size={11} /> NCLT Active
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-3 text-sm text-slate-500 mb-3">
              {(dev.city_hq || dev.headquarters_city) && (
                <span className="flex items-center gap-1">
                  <MapPin size={13} /> {dev.city_hq ?? dev.headquarters_city}
                </span>
              )}
              {dev.incorporation_year && (
                <span className="flex items-center gap-1">
                  <Calendar size={13} /> Est. {dev.incorporation_year}
                </span>
              )}
              {dev.cin && (
                <span className="flex items-center gap-1 font-mono text-xs">
                  CIN: {dev.cin}
                </span>
              )}
            </div>

            {dev.description && (
              <p className="text-sm text-slate-600 leading-relaxed line-clamp-2">{dev.description}</p>
            )}
          </div>

          {/* Financial stress gauge */}
          {stressScore !== null && (
            <div className="shrink-0 text-center">
              <ScoreGauge
                score={stressScore}
                size={120}
                label="Financial Health"
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Projects Delivered"
          value={delivered}
          icon={Building2}
          color="text-propiq-navy"
        />
        <StatCard
          label="On-time Rate"
          value={`${Math.round(onTimePct)}%`}
          icon={Clock}
          color={onTimePct >= 70 ? 'text-risk-low' : onTimePct >= 50 ? 'text-risk-medium' : 'text-risk-high'}
        />
        {totalUnits != null ? (
          <StatCard
            label="Total Units Delivered"
            value={totalUnits.toLocaleString('en-IN')}
            icon={Users}
            color="text-propiq-teal"
          />
        ) : (
          <StatCard
            label="Ongoing Projects"
            value={(dev.ongoing_projects ?? 0)}
            icon={TrendingUp}
            color="text-propiq-blue"
          />
        )}
        <StatCard
          label="Active Complaints"
          value={complaints}
          icon={MessageSquare}
          color={complaints === 0 ? 'text-risk-low' : complaints < 10 ? 'text-risk-medium' : 'text-risk-high'}
        />
      </div>

      {/* On-time progress bar */}
      <div className="bg-white rounded-2xl shadow-card p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-semibold text-propiq-navy">Delivery Track Record</p>
          <span className="text-xs text-slate-500">
            {Math.round(onTimePct)}% on time out of {delivered} projects
          </span>
        </div>
        <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full rounded-full transition-all duration-700"
            style={{
              width: `${onTimePct}%`,
              background: onTimePct >= 70 ? '#15803d' : onTimePct >= 50 ? '#b45309' : '#c2410c',
            }}
          />
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
          {dev.delayed_projects != null && (
            <span className="flex items-center gap-1">
              <AlertTriangle size={11} className="text-risk-high" />
              {dev.delayed_projects} delayed
            </span>
          )}
          {dev.average_delay_months != null && dev.average_delay_months > 0 && (
            <span>Avg delay: {Math.round(dev.average_delay_months)} months</span>
          )}
          {onTimePct >= 80 && (
            <span className="flex items-center gap-1 text-risk-low">
              <CheckCircle2 size={11} /> Strong delivery record
            </span>
          )}
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-slate-200 mb-5">
        {tabs.map(({ id: tid, label }) => (
          <button
            key={tid}
            onClick={() => setTab(tid)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === tid
                ? 'border-propiq-navy text-propiq-navy'
                : 'border-transparent text-slate-500 hover:text-propiq-navy'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      {tab === 'projects' && (
        <div className="space-y-2.5">
          {projects.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <Building2 size={32} className="mx-auto mb-3 opacity-30" />
              <p>No projects found for this developer.</p>
            </div>
          ) : (
            projects.map((p) => (
              <ProjectListItem
                key={p.id}
                project={p as unknown as import('@/types').ProjectWithScore}
                riskScore={p.risk_score as RiskScoreBrief | undefined}
              />
            ))
          )}
        </div>
      )}

      {tab === 'complaints' && (
        <div className="space-y-3">
          {complaints === 0 ? (
            <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
              <CheckCircle2 size={28} className="mx-auto mb-2 text-risk-low" />
              <p className="font-semibold text-risk-low">No active complaints</p>
              <p className="text-sm text-slate-500 mt-1">This developer has a clean complaint record.</p>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center">
              <AlertTriangle size={28} className="mx-auto mb-2 text-risk-medium" />
              <p className="font-semibold text-risk-medium">{complaints} active complaint{complaints !== 1 ? 's' : ''}</p>
              <p className="text-sm text-slate-500 mt-1">Check RERA portal for full complaint details.</p>
              <a
                href="https://rera.maharashtra.gov.in"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-xs text-propiq-blue hover:underline"
              >
                View on RERA <ExternalLink size={11} />
              </a>
            </div>
          )}
        </div>
      )}

      {tab === 'news' && (
        <div className="bg-white rounded-2xl shadow-card p-6">
          {dev.nclt_proceedings && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl mb-4">
              <AlertTriangle size={16} className="text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-700 text-sm">NCLT Proceedings Active</p>
                <p className="text-xs text-slate-600 mt-0.5">
                  This developer has active proceedings at the National Company Law Tribunal.
                  Exercise extra caution before investing.
                </p>
              </div>
            </div>
          )}
          <p className="text-sm text-slate-500 text-center py-8">
            News and alerts aggregation coming soon. Check back for real-time updates from RERA portals,
            court records, and news sources.
          </p>
        </div>
      )}

      {/* Back link */}
      <div className="mt-8">
        <Button variant="secondary" size="sm" onClick={() => history.back()}>
          ← Back
        </Button>
      </div>
    </div>
  )
}
