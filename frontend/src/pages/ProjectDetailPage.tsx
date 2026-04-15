import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, RefreshCw, Download, Share2, Loader2,
  MapPin, Calendar, AlertTriangle, CheckCircle2,
  Newspaper, TrendingUp, Info,
} from 'lucide-react'
import { useProjectDetail } from '@/hooks'
import { useAuthStore, useUIStore } from '@/store'
import {
  ScoreGauge, RiskBreakdownBar, AppreciationCard,
  RiskScoreBadge, DeveloperCard, ProjectCard, UpgradeGate,
  Badge, Skeleton, Button, ProjectMap,
} from '@/components'
import { apiClient } from '@/services/api'
import {
  formatDate, formatPSF, formatDelay, formatScore,
  formatCAGR, getRiskBgClass, getRiskLabel,
} from '@/utils/formatters'
import type { ProjectDetail } from '@/types'

// ── Tabs ──────────────────────────────────────────────────────────────────────

type Tab = 'overview' | 'risk' | 'appreciation' | 'developer' | 'similar'
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview',     label: 'Overview' },
  { id: 'risk',         label: 'Risk Breakdown' },
  { id: 'appreciation', label: 'Appreciation' },
  { id: 'developer',    label: 'Developer' },
  { id: 'similar',      label: 'Similar' },
]

// ── Simple SVG line chart ────────────────────────────────────────────────────

interface ChartPoint { year: string; project: number; cityAvg: number }

function LineChart({ data }: { data: ChartPoint[] }) {
  const W = 480, H = 180, PAD = 36
  const vals = data.flatMap((d) => [d.project, d.cityAvg])
  const min = Math.min(...vals) * 0.95
  const max = Math.max(...vals) * 1.05
  const rx = (i: number) => PAD + (i / (data.length - 1)) * (W - PAD * 2)
  const ry = (v: number) => H - PAD - ((v - min) / (max - min)) * (H - PAD * 2)
  const path = (key: 'project' | 'cityAvg') =>
    data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${rx(i)} ${ry(d[key])}`).join(' ')

  return (
    <div className="relative">
      <div className="flex gap-4 text-xs text-slate-500 mb-2 justify-end">
        <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-propiq-blue inline-block rounded" /> This micromarket</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-slate-300 inline-block rounded border-dashed" /> City avg</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full overflow-visible">
        {/* Grid */}
        {[0.25, 0.5, 0.75, 1].map((t) => (
          <line key={t} x1={PAD} y1={ry(min + t * (max - min))} x2={W - PAD} y2={ry(min + t * (max - min))}
            stroke="#f1f5f9" strokeWidth="1" />
        ))}
        {/* Avg line */}
        <path d={path('cityAvg')} fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="4 3" strokeLinecap="round" strokeLinejoin="round" />
        {/* Project line */}
        <path d={path('project')} fill="none" stroke="#2E6DA4" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {/* Dots + X labels */}
        {data.map((d, i) => (
          <g key={d.year}>
            <circle cx={rx(i)} cy={ry(d.project)} r="4" fill="#2E6DA4" />
            <text x={rx(i)} y={H - 4} textAnchor="middle" fontSize="11" fill="#94a3b8">{d.year}</text>
          </g>
        ))}
        {/* Y axis first/last labels */}
        <text x={PAD - 4} y={ry(max)} textAnchor="end" fontSize="10" fill="#94a3b8">
          ₹{(max / 1000).toFixed(0)}K
        </text>
        <text x={PAD - 4} y={ry(min)} textAnchor="end" fontSize="10" fill="#94a3b8">
          ₹{(min / 1000).toFixed(0)}K
        </text>
      </svg>
    </div>
  )
}

// ── Return calculator ────────────────────────────────────────────────────────

function ReturnCalculator({ appreciation }: { appreciation: ProjectDetail['appreciation'] }) {
  const [amount, setAmount]   = useState(5000000)
  const [period, setPeriod]   = useState<3 | 5>(3)
  const [leverage, setLeverage] = useState(false)

  const cagr = period === 3 ? (appreciation?.cagr_3yr_base ?? 10) : (appreciation?.cagr_5yr_base ?? 12)
  const invested = leverage ? amount * 0.5 : amount
  const fv = amount * Math.pow(1 + cagr / 100, period)
  const profit = fv - amount
  const annualized = ((fv / invested) ** (1 / period) - 1) * 100

  const fmt = (n: number) =>
    n >= 1e7 ? `₹${(n / 1e7).toFixed(2)} Cr` : n >= 1e5 ? `₹${(n / 1e5).toFixed(1)} L` : `₹${n.toLocaleString('en-IN')}`

  return (
    <div className="bg-navy-50 border border-navy-100 rounded-2xl p-5">
      <h4 className="font-bold text-propiq-navy mb-4">Return Calculator</h4>
      <div className="grid sm:grid-cols-2 gap-4 mb-5">
        <div>
          <label className="text-xs font-medium text-slate-500 block mb-1">Investment Amount</label>
          <select
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-propiq-blue/30"
          >
            {[2500000, 5000000, 10000000, 20000000, 50000000].map((v) => (
              <option key={v} value={v}>{fmt(v)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-500 block mb-1">Holding Period</label>
          <div className="flex gap-2">
            {([3, 5] as const).map((p) => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`flex-1 py-2 text-sm font-medium rounded-lg border transition-all ${period === p ? 'bg-propiq-navy text-white border-propiq-navy' : 'border-slate-200 text-slate-600 hover:border-propiq-blue'}`}>
                {p} years
              </button>
            ))}
          </div>
        </div>
      </div>

      <label className="flex items-center gap-2.5 cursor-pointer mb-5">
        <input type="checkbox" checked={leverage} onChange={(e) => setLeverage(e.target.checked)}
          className="w-4 h-4 rounded border-slate-300 text-propiq-blue focus:ring-propiq-blue" />
        <span className="text-sm text-slate-700">Use leverage (50% LTV home loan)</span>
      </label>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Expected Value', value: fmt(fv), color: 'text-propiq-navy' },
          { label: 'Profit / Loss', value: fmt(profit), color: profit >= 0 ? 'text-risk-low' : 'text-risk-critical' },
          { label: 'Annualized Return', value: formatCAGR(annualized), color: 'text-propiq-blue' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl p-3 text-center border border-slate-100">
            <p className="text-2xs text-slate-500 mb-1">{label}</p>
            <p className={`font-mono font-bold text-sm ${color}`}>{value}</p>
          </div>
        ))}
      </div>
      <p className="text-2xs text-slate-400 mt-3 text-center">
        Uses {period}yr base CAGR of {formatCAGR(cagr)}. Not financial advice.
      </p>
    </div>
  )
}

// ── PDF download hook ────────────────────────────────────────────────────────

function useDownloadReport(projectId: string | undefined) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const { openAuthModal, openUpgradeModal } = useUIStore()
  const { user } = useAuthStore()

  const download = useCallback(async () => {
    if (!projectId) return
    if (!user) { openAuthModal(); return }
    if (user.subscription_tier !== 'pro' && user.subscription_tier !== 'enterprise') {
      openUpgradeModal(); return
    }

    setIsDownloading(true)
    setDownloadError(null)
    try {
      const response = await apiClient.post(
        `/diligence/report/${projectId}`,
        {},
        { responseType: 'blob', timeout: 90_000 },
      )
      const blob = new Blob([response.data as BlobPart], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const disposition = response.headers['content-disposition'] as string | undefined
      const match = disposition?.match(/filename="([^"]+)"/)
      a.download = match?.[1] ?? `propiq-report-${projectId}.pdf`
      a.href = url
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 403) {
        openUpgradeModal()
      } else {
        setDownloadError('Report generation failed. Please try again.')
      }
    } finally {
      setIsDownloading(false)
    }
  }, [projectId, user, openAuthModal, openUpgradeModal])

  return { download, isDownloading, downloadError }
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const { user } = useAuthStore()

  const isPro = user?.subscription_tier === 'pro' || user?.subscription_tier === 'enterprise'

  const { data: project, isLoading, isError, refetch } = useProjectDetail(id)
  const { download, isDownloading, downloadError } = useDownloadReport(id)

  useEffect(() => {
    document.title = project ? `${project.name} — PropIQ` : 'Project Detail — PropIQ'
  }, [project])

  if (isLoading) return <LoadingState />

  if (isError || !project) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <p className="text-5xl mb-4">🏗</p>
        <h2 className="text-xl font-bold text-propiq-navy mb-2">Project not found</h2>
        <p className="text-slate-500 mb-4">This project may not be in our database yet.</p>
        <Button variant="secondary" onClick={() => refetch()}>Retry</Button>
      </div>
    )
  }

  const rs = project.current_risk_score
  const dev = project.developer
  const score = rs?.composite_score ?? rs?.overall_score ?? 0
  const possessionDate = project.possession_date_latest ?? project.revised_possession_date ?? project.possession_date_declared ?? project.rera_possession_date
  const delay = formatDelay(project.possession_date_declared ?? project.rera_possession_date, project.possession_date_latest ?? project.revised_possession_date)
  const isDelayed = delay && delay !== 'On track'
  const construction = project.construction_pct ?? project.construction_progress_pct ?? 0
  const totalUnits = project.total_units ?? 0
  const soldUnits = project.units_sold ?? project.sold_units ?? 0

  // Mock chart data
  const basePSF = project.price_psf_min ?? project.price_per_sqft_min ?? 8000
  const chartData: ChartPoint[] = [
    { year: '2020', project: basePSF * 0.72, cityAvg: basePSF * 0.78 },
    { year: '2021', project: basePSF * 0.80, cityAvg: basePSF * 0.83 },
    { year: '2022', project: basePSF * 0.90, cityAvg: basePSF * 0.90 },
    { year: '2023', project: basePSF * 0.96, cityAvg: basePSF * 0.95 },
    { year: '2024', project: basePSF,         cityAvg: basePSF * 0.97 },
  ]

  const allFlags = [
    ...((rs?.legal_flags) ?? []).map((f) => ({ text: f, type: 'legal' as const })),
    ...((rs?.developer_flags) ?? []).map((f) => ({ text: f, type: 'developer' as const })),
    ...((rs?.project_flags) ?? []).map((f) => ({ text: f, type: 'project' as const })),
  ]
  const criticalFlags = allFlags.filter((_, i) => score < 40 || i < 2)
  const warningFlags  = allFlags.filter((_, i) => i >= 2)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Back */}
      <Link to="/search" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-propiq-blue mb-5 transition-colors">
        <ArrowLeft size={14} /> Back to results
      </Link>

      {/* Project header */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex-1">
            <div className="flex flex-wrap gap-2 mb-2">
              {project.rera_status && (
                <Badge
                  label={`RERA: ${project.rera_status.toUpperCase()}`}
                  color={project.rera_status === 'active' ? 'green' : 'red'}
                  dot
                />
              )}
              {project.project_type && (
                <Badge label={project.project_type} color="blue" />
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-propiq-navy mb-1">{project.name}</h1>
            <p className="text-slate-500 flex items-center gap-1.5">
              {dev?.name && <><span className="font-medium text-propiq-blue">{dev.name}</span><span className="text-slate-300">·</span></>}
              <MapPin size={13} />
              {[project.micromarket || project.locality, project.city].filter(Boolean).join(', ')}
            </p>
          </div>

          {rs && (
            <div className="flex flex-col items-center">
              <ScoreGauge score={score} size={130} />
              <span className={`mt-1 text-xs font-bold uppercase tracking-wide ${getRiskBgClass(rs.risk_band)} px-2 py-0.5 rounded-full`}>
                {getRiskLabel(rs.risk_band)}
              </span>
            </div>
          )}
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-5 border-t border-slate-50">
          <StatChip label="Price / sqft"
            value={formatPSF(project.price_psf_min ?? project.price_per_sqft_min)} />
          <StatChip label="Possession"
            value={formatDate(possessionDate)}
            sub={isDelayed ? delay ?? undefined : undefined}
            subColor="text-risk-medium" />
          <StatChip label="Construction" value={`${Math.round(construction)}%`} />
          <StatChip label="Units Sold"
            value={totalUnits > 0 ? `${Math.round((soldUnits / totalUnits) * 100)}%` : '—'}
            sub={`${soldUnits} / ${totalUnits}`} />
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 mt-4 flex-wrap items-center">
          <Button variant="ghost" size="sm" leftIcon={<Share2 size={13} />}
            onClick={() => navigator.clipboard?.writeText(window.location.href)}>
            Share
          </Button>
          <Button variant="ghost" size="sm" leftIcon={<RefreshCw size={13} />}>
            Refresh data
          </Button>
          {isPro ? (
            <Button
              variant="primary"
              size="sm"
              leftIcon={isDownloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
              onClick={download}
              disabled={isDownloading}
            >
              {isDownloading ? 'Generating…' : 'Download PDF Report'}
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<Download size={13} />}
              onClick={() => useUIStore.getState().openUpgradeModal()}
              className="text-amber-600 border-amber-200 hover:bg-amber-50"
            >
              PDF Report
              <span className="ml-1.5 text-2xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-semibold">Pro</span>
            </Button>
          )}
          {downloadError && (
            <p className="text-xs text-red-500 flex items-center gap-1">
              <AlertTriangle size={11} /> {downloadError}
            </p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-propiq-navy text-propiq-navy'
                : 'border-transparent text-slate-500 hover:text-propiq-navy'
            }`}
          >
            {tab.label}
            {(tab.id === 'risk' || tab.id === 'appreciation') && !isPro && (
              <span className="ml-1.5 text-2xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-semibold">Pro</span>
            )}
          </button>
        ))}
      </div>

      {/* ── TAB: OVERVIEW ── */}
      {activeTab === 'overview' && (
        <div className="space-y-6 animate-fade-in">
          {/* Interactive map */}
          <ProjectMap
            projectId={project.id}
            projectName={project.name}
            city={project.city}
            micromarket={project.micromarket}
            latitude={project.latitude}
            longitude={project.longitude}
            heightClass="h-80"
          />

          {/* Progress bars: construction + units sold */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
            <h3 className="font-bold text-propiq-navy mb-4">Project Status</h3>
            <div className="space-y-4">
              <ProgressRow label="Construction Progress" pct={construction} color="bg-propiq-blue" />
              {totalUnits > 0 && (
                <ProgressRow label={`Units Sold (${soldUnits} / ${totalUnits})`} pct={(soldUnits / totalUnits) * 100} color="bg-propiq-teal" />
              )}
            </div>
          </div>

          {/* News */}
          {project.recent_news?.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
              <h3 className="font-bold text-propiq-navy mb-4 flex items-center gap-2">
                <Newspaper size={16} /> Recent News
              </h3>
              <div className="space-y-3">
                {project.recent_news.slice(0, 3).map((n) => {
                  const sent = n.sentiment_score ?? 0
                  return (
                    <a key={n.id} href={n.url ?? '#'} target="_blank" rel="noopener noreferrer"
                      className="flex gap-3 hover:bg-slate-50 rounded-xl p-2 -mx-2 transition-colors group">
                      <span className={`text-lg ${sent > 0.2 ? '😊' : sent < -0.2 ? '😟' : '😐'}`} aria-hidden />
                      <div>
                        <p className="text-sm font-medium text-propiq-navy group-hover:text-propiq-blue line-clamp-2">{n.title}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{n.source} · {formatDate(n.published_at)}</p>
                      </div>
                    </a>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: RISK BREAKDOWN ── */}
      {activeTab === 'risk' && (
        <UpgradeGate isLocked={!isPro} feature="Risk Breakdown">
          <div className="space-y-6 animate-fade-in">
            {rs && (
              <>
                <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
                  <h3 className="font-bold text-propiq-navy mb-5">Dimension Scores</h3>
                  <div className="space-y-4">
                    <RiskBreakdownBar label="Legal & Compliance"  score={rs.legal_score ?? 0}     weight={25} flags={rs.legal_flags ?? []} />
                    <RiskBreakdownBar label="Developer Track"      score={rs.developer_score ?? 0}  weight={25} flags={rs.developer_flags ?? []} />
                    <RiskBreakdownBar label="Project Health"       score={rs.project_score ?? 0}    weight={20} flags={rs.project_flags ?? []} />
                    <RiskBreakdownBar label="Location Quality"     score={rs.location_score ?? 0}   weight={15} />
                    <RiskBreakdownBar label="Financial Indicators" score={rs.financial_score ?? 0}  weight={10} />
                    <RiskBreakdownBar label="Macro Environment"    score={rs.macro_score ?? 0}      weight={5}  />
                  </div>
                </div>

                {/* Flag cards */}
                {allFlags.length > 0 && (
                  <div className="space-y-3">
                    {criticalFlags.length > 0 && <FlagCard title="Critical Flags" flags={criticalFlags.map(f => f.text)} color="red" />}
                    {warningFlags.length > 0  && <FlagCard title="Warning Flags"  flags={warningFlags.map(f => f.text)}  color="amber" />}
                  </div>
                )}

                {/* Data freshness */}
                <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
                  <h3 className="font-bold text-propiq-navy mb-4 flex items-center gap-2">
                    <Info size={15} /> Data Freshness
                  </h3>
                  <table className="w-full text-sm">
                    <tbody>
                      {[
                        ['RERA Project Data', project.last_scraped_at ? `${Math.round((Date.now() - new Date(project.last_scraped_at).getTime()) / 86400000)} days ago` : 'Unknown'],
                        ['Risk Score Computed', rs.computed_at ? formatDate(rs.computed_at) : formatDate(rs.generated_at)],
                        ['Developer Data', dev?.last_scraped_at ? `${Math.round((Date.now() - new Date(dev.last_scraped_at).getTime()) / 86400000)} days ago` : 'Unknown'],
                      ].map(([label, value]) => (
                        <tr key={label} className="border-b border-slate-50 last:border-0">
                          <td className="py-2.5 text-slate-500">{label}</td>
                          <td className="py-2.5 text-right font-medium text-propiq-navy">{value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </UpgradeGate>
      )}

      {/* ── TAB: APPRECIATION ── */}
      {activeTab === 'appreciation' && (
        <UpgradeGate isLocked={!isPro} feature="Appreciation Forecast">
          <div className="space-y-6 animate-fade-in">
            {project.appreciation && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6">
                <h3 className="font-bold text-propiq-navy mb-5">Appreciation Forecast</h3>
                <AppreciationCard appreciation={project.appreciation} />
              </div>
            )}

            {/* Historical chart */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6">
              <h3 className="font-bold text-propiq-navy mb-4">Historical Price Trend (₹/sqft)</h3>
              <LineChart data={chartData} />
            </div>

            {/* Return calculator */}
            {project.appreciation && <ReturnCalculator appreciation={project.appreciation} />}
          </div>
        </UpgradeGate>
      )}

      {/* ── TAB: DEVELOPER ── */}
      {activeTab === 'developer' && (
        <div className="space-y-6 animate-fade-in">
          {dev && <DeveloperCard developer={dev} />}
          {project.recent_news?.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
              <h3 className="font-bold text-propiq-navy mb-4">Developer News</h3>
              <div className="space-y-3">
                {project.recent_news.map((n) => (
                  <a key={n.id} href={n.url ?? '#'} target="_blank" rel="noopener noreferrer"
                    className="flex gap-3 hover:bg-slate-50 p-2 -mx-2 rounded-xl transition-colors group">
                    <TrendingUp size={14} className={`mt-1 shrink-0 ${(n.sentiment_score ?? 0) > 0 ? 'text-risk-low' : (n.sentiment_score ?? 0) < 0 ? 'text-risk-critical' : 'text-slate-400'}`} />
                    <div>
                      <p className="text-sm font-medium text-propiq-navy group-hover:text-propiq-blue line-clamp-2">{n.title}</p>
                      <p className="text-xs text-slate-400">{n.source} · {formatDate(n.published_at)}</p>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: SIMILAR ── */}
      {activeTab === 'similar' && (
        <div className="animate-fade-in">
          <p className="text-sm text-slate-500 mb-4">
            Projects in <strong>{project.city}</strong> with similar price range and better risk scores.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Placeholder cards — in production, fetch similar projects */}
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl border border-slate-100 shadow-card p-5 text-center py-10">
                <p className="text-slate-400 text-sm">Similar project {i + 1}</p>
                <p className="text-xs text-slate-300 mt-1">Loading similar projects…</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
      <Skeleton height={24} width={120} />
      <div className="bg-white rounded-2xl border p-6 space-y-4">
        <div className="flex justify-between">
          <div className="space-y-2"><Skeleton height={32} width={280} /><Skeleton height={16} width={180} /></div>
          <Skeleton width={130} height={130} rounded="full" />
        </div>
        <div className="grid grid-cols-4 gap-3">
          {Array.from({length:4}).map((_,i)=><Skeleton key={i} height={60} rounded="lg"/>)}
        </div>
      </div>
    </div>
  )
}

function StatChip({ label, value, sub, subColor }: { label: string; value: string; sub?: string; subColor?: string }) {
  return (
    <div>
      <p className="text-2xs text-slate-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className="font-mono font-bold text-propiq-navy text-sm">{value}</p>
      {sub && <p className={`text-2xs ${subColor ?? 'text-slate-400'}`}>{sub}</p>}
    </div>
  )
}

function ProgressRow({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="font-mono font-bold text-propiq-navy">{Math.round(pct)}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function FlagCard({ title, flags, color }: { title: string; flags: string[]; color: 'red' | 'amber' }) {
  const cls = color === 'red'
    ? 'bg-red-50 border-red-200 text-red-700'
    : 'bg-amber-50 border-amber-200 text-amber-700'
  return (
    <div className={`rounded-2xl border p-5 ${cls}`}>
      <h4 className="font-bold mb-3 flex items-center gap-2">
        <AlertTriangle size={15} /> {title}
      </h4>
      <ul className="space-y-1.5">
        {flags.map((f) => (
          <li key={f} className="text-sm flex items-start gap-2">
            <span aria-hidden className="mt-0.5">•</span>{f}
          </li>
        ))}
      </ul>
    </div>
  )
}
