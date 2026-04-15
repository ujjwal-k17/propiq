import { useNavigate } from 'react-router-dom'
import { Building2, CheckCircle2, AlertCircle, MapPin, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import type { Developer } from '@/types'
import { Badge } from '@/components/ui/Badge'

export interface DeveloperCardProps {
  developer: Developer
  className?: string
}

function StressIndicator({ score }: { score: number | null }) {
  if (score == null) return null
  const isLow = score < 30
  const isMed = score < 60
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={clsx(
          'w-2.5 h-2.5 rounded-full shrink-0',
          isLow ? 'bg-risk-low' : isMed ? 'bg-risk-medium' : 'bg-risk-critical',
        )}
      />
      <span className={clsx(
        'text-xs font-medium',
        isLow ? 'text-risk-low' : isMed ? 'text-risk-medium' : 'text-risk-critical',
      )}>
        {isLow ? 'Low' : isMed ? 'Moderate' : 'High'} financial stress
      </span>
    </div>
  )
}

export function DeveloperCard({ developer, className }: DeveloperCardProps) {
  const navigate = useNavigate()
  const hq = developer.city_hq ?? developer.headquarters_city

  const onTime = developer.projects_on_time_pct
  const onTimeColor =
    onTime == null ? 'gray'
    : onTime >= 70 ? 'green'
    : onTime >= 40 ? 'amber'
    : 'red'

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/developers/${developer.id}`)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && navigate(`/developers/${developer.id}`)}
      className={clsx(
        'group bg-white rounded-2xl border border-slate-100 shadow-card p-5',
        'cursor-pointer transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5 hover:border-propiq-blue/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy focus-visible:ring-offset-2',
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-navy-50 flex items-center justify-center shrink-0">
            <Building2 size={18} className="text-propiq-navy" />
          </div>
          <div>
            <h3 className="font-semibold text-propiq-navy group-hover:text-propiq-blue transition-colors leading-snug">
              {developer.name}
            </h3>
            {hq && (
              <p className="text-xs text-slate-400 flex items-center gap-0.5 mt-0.5">
                <MapPin size={10} /> {hq}
              </p>
            )}
          </div>
        </div>

        {developer.nclt_proceedings && (
          <Badge label="NCLT" color="red" dot />
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <Stat label="Projects Delivered" value={developer.total_projects_delivered.toString()} />
        <Stat
          label="On-Time %"
          value={onTime != null ? `${onTime.toFixed(0)}%` : '—'}
          color={onTimeColor}
        />
        <Stat
          label="Active Complaints"
          value={developer.active_complaint_count.toString()}
          color={developer.active_complaint_count > 10 ? 'red' : developer.active_complaint_count > 3 ? 'amber' : 'green'}
        />
      </div>

      {/* Financial stress */}
      <StressIndicator score={developer.financial_stress_score} />

      {/* Delivery track record pill */}
      {onTime != null && (
        <div className="mt-3 flex items-center gap-1.5 text-xs">
          {onTime >= 70 ? (
            <CheckCircle2 size={13} className="text-risk-low" />
          ) : onTime >= 40 ? (
            <AlertTriangle size={13} className="text-risk-medium" />
          ) : (
            <AlertCircle size={13} className="text-risk-critical" />
          )}
          <span className="text-slate-500">
            {onTime >= 70
              ? 'Strong delivery track record'
              : onTime >= 40
              ? 'Mixed delivery history'
              : 'Poor delivery track record'}
          </span>
        </div>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  color = 'gray',
}: {
  label: string
  value: string
  color?: 'green' | 'amber' | 'red' | 'gray'
}) {
  const colorCls: Record<string, string> = {
    green: 'text-risk-low',
    amber: 'text-risk-medium',
    red:   'text-risk-critical',
    gray:  'text-propiq-navy',
  }
  return (
    <div className="text-center">
      <p className={clsx('font-mono font-bold text-base leading-none mb-1 tabular-nums', colorCls[color])}>
        {value}
      </p>
      <p className="text-2xs text-slate-400 leading-tight">{label}</p>
    </div>
  )
}
