import { useNavigate } from 'react-router-dom'
import { MapPin, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import type { Project, RiskScoreBrief } from '@/types'
import { RiskScoreBadge } from '@/components/ui/RiskScoreBadge'
import { formatPSF, formatDate } from '@/utils/formatters'

export interface ProjectListItemProps {
  project: Project | { id: string; name: string; developer_name?: string | null; city: string; locality?: string | null; micromarket?: string; price_psf_min?: number | null; price_per_sqft_min?: number | null; rera_possession_date?: string | null; possession_date_latest?: string | null }
  riskScore?: RiskScoreBrief | null
  onSelect?: () => void
  selected?: boolean
  className?: string
}

export function ProjectListItem({
  project,
  riskScore,
  onSelect,
  selected = false,
  className,
}: ProjectListItemProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (onSelect) { onSelect(); return }
    navigate(`/projects/${project.id}`)
  }

  const score = riskScore?.composite_score ?? riskScore?.overall_score
  const band = riskScore?.risk_band

  const minPSF = ('price_psf_min' in project ? project.price_psf_min : null)
    ?? ('price_per_sqft_min' in project ? project.price_per_sqft_min : null)

  const possession = ('possession_date_latest' in project ? project.possession_date_latest : null)
    ?? ('rera_possession_date' in project ? project.rera_possession_date : null)

  const location = [
    ('micromarket' in project ? project.micromarket : null)
    || ('locality' in project ? project.locality : null),
    project.city,
  ].filter(Boolean).join(', ')

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick()}
      aria-pressed={selected}
      className={clsx(
        'flex items-center gap-3 p-4 rounded-xl border transition-all duration-150 cursor-pointer group',
        selected
          ? 'bg-navy-50 border-propiq-blue shadow-sm'
          : 'bg-white border-slate-100 hover:border-propiq-blue/40 hover:bg-slate-50',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy',
        className,
      )}
    >
      {/* Risk badge */}
      {score != null && band ? (
        <div className="shrink-0">
          <RiskScoreBadge score={score} band={band} size="sm" showLabel={false} />
        </div>
      ) : (
        <div className="w-10 h-10 rounded-full bg-slate-100 shrink-0" />
      )}

      {/* Middle: name + developer + location */}
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm text-propiq-navy truncate group-hover:text-propiq-blue transition-colors">
          {project.name}
        </p>
        <p className="text-xs text-slate-500 truncate">
          {'developer_name' in project && project.developer_name
            ? `${project.developer_name} · `
            : ''}
          <MapPin size={9} className="inline mr-0.5" />
          {location}
        </p>
      </div>

      {/* Right: price + possession */}
      <div className="shrink-0 text-right hidden sm:block">
        {minPSF && (
          <p className="text-xs font-mono font-semibold text-propiq-navy">{formatPSF(minPSF)}</p>
        )}
        {possession && (
          <p className="text-2xs text-slate-400">{formatDate(possession)}</p>
        )}
      </div>

      <ChevronRight size={14} className="shrink-0 text-slate-300 group-hover:text-propiq-blue transition-colors" />
    </div>
  )
}
