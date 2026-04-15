import { useNavigate } from 'react-router-dom'
import { MapPin, Calendar, Building2, TrendingUp } from 'lucide-react'
import clsx from 'clsx'
import type { Project, RiskScoreBrief } from '@/types'
import { RiskScoreBadge } from '@/components/ui/RiskScoreBadge'
import { formatPSF, formatDate, formatDelay } from '@/utils/formatters'

export interface ProjectCardProps {
  project: Project
  riskScore?: RiskScoreBrief | null
  onClick?: () => void
  className?: string
}

export function ProjectCard({ project, riskScore, onClick, className }: ProjectCardProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (onClick) { onClick(); return }
    navigate(`/projects/${project.id}`)
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick() }
  }

  // Derive possession date — prefer spec field, fall back to legacy
  const possessionDeclared = project.possession_date_declared ?? project.rera_possession_date
  const possessionLatest = project.possession_date_latest ?? project.revised_possession_date

  const delay = possessionDeclared && possessionLatest
    ? formatDelay(possessionDeclared, possessionLatest)
    : null

  const isDelayed = delay && delay !== 'On track'

  // Construction progress
  const progress = project.construction_pct ?? project.construction_progress_pct
  const isUnderConstruction =
    project.status === 'under_construction' || (progress != null && progress < 100)

  // Price
  const minPSF = project.price_psf_min ?? project.price_per_sqft_min
  const maxPSF = project.price_psf_max ?? project.price_per_sqft_max

  const priceStr =
    minPSF && maxPSF
      ? `${formatPSF(minPSF)} – ${formatPSF(maxPSF)}`
      : minPSF
      ? formatPSF(minPSF)
      : '—'

  const score = riskScore?.composite_score ?? riskScore?.overall_score
  const band = riskScore?.risk_band

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKey}
      aria-label={`View ${project.name} details`}
      className={clsx(
        'group relative bg-white rounded-2xl border border-slate-100 shadow-card',
        'cursor-pointer transition-all duration-200',
        'hover:shadow-card-hover hover:-translate-y-0.5 hover:border-propiq-blue/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy focus-visible:ring-offset-2',
        'p-5',
        className,
      )}
    >
      {/* Risk badge — top right */}
      {score != null && band && (
        <div className="absolute top-4 right-4">
          <RiskScoreBadge score={score} band={band} size="md" showLabel />
        </div>
      )}

      {/* Header */}
      <div className="pr-20 mb-3">
        <h3 className="font-semibold text-propiq-navy text-base leading-snug group-hover:text-propiq-blue transition-colors line-clamp-2">
          {project.name}
        </h3>
        {project.developer_name && (
          <p className="text-sm text-slate-500 mt-0.5 flex items-center gap-1">
            <Building2 size={12} className="shrink-0" />
            {project.developer_name}
          </p>
        )}
      </div>

      {/* Location */}
      <div className="flex items-center gap-1 text-xs text-slate-400 mb-3">
        <MapPin size={11} className="shrink-0" />
        <span>{[project.micromarket || project.locality, project.city].filter(Boolean).join(', ')}</span>
      </div>

      {/* Construction progress */}
      {isUnderConstruction && progress != null && (
        <div className="mb-3">
          <div className="flex justify-between text-2xs text-slate-400 mb-1">
            <span>Construction</span>
            <span className="font-mono font-medium text-propiq-navy">{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-propiq-blue to-propiq-teal transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-50">
        <StatCell label="Price / sqft" value={priceStr} mono />
        <StatCell
          label="Possession"
          value={formatDate(possessionLatest ?? possessionDeclared)}
          icon={isDelayed ? <Calendar size={10} className="text-risk-medium" /> : undefined}
          valueClass={isDelayed ? 'text-risk-medium' : undefined}
        />
        <StatCell
          label="Units"
          value={project.total_units != null ? project.total_units.toString() : '—'}
          mono
        />
      </div>

      {/* Delay tag */}
      {isDelayed && (
        <div className="mt-2 inline-flex items-center gap-1 text-2xs bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-2 py-0.5 font-medium">
          <TrendingUp size={9} className="rotate-90" />
          {delay}
        </div>
      )}
    </div>
  )
}

function StatCell({
  label,
  value,
  mono,
  icon,
  valueClass,
}: {
  label: string
  value: string
  mono?: boolean
  icon?: React.ReactNode
  valueClass?: string
}) {
  return (
    <div>
      <p className="text-2xs text-slate-400 uppercase tracking-wide mb-0.5">{label}</p>
      <p className={clsx('text-xs font-semibold text-slate-700 flex items-center gap-0.5', mono && 'font-mono', valueClass)}>
        {icon}{value}
      </p>
    </div>
  )
}
