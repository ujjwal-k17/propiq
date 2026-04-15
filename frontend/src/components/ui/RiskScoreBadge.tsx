import clsx from 'clsx'
import type { RiskBand } from '@/types'

export interface RiskScoreBadgeProps {
  score: number
  band: RiskBand | string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

const sizeMap = {
  sm: { circle: 'w-10 h-10',  score: 'text-sm font-bold',    label: 'text-2xs', gap: 'gap-0.5' },
  md: { circle: 'w-16 h-16',  score: 'text-lg font-extrabold', label: 'text-2xs', gap: 'gap-0.5' },
  lg: { circle: 'w-24 h-24',  score: 'text-3xl font-extrabold', label: 'text-xs', gap: 'gap-1'   },
}

const bandStyles: Record<string, { bg: string; text: string; ring: string; label: string }> = {
  low:      { bg: 'bg-green-50',  text: 'text-risk-low',      ring: 'ring-risk-low/30',      label: 'Low' },
  medium:   { bg: 'bg-amber-50',  text: 'text-risk-medium',   ring: 'ring-risk-medium/30',   label: 'Medium' },
  high:     { bg: 'bg-orange-50', text: 'text-risk-high',     ring: 'ring-risk-high/30',     label: 'High' },
  critical: { bg: 'bg-red-50',    text: 'text-risk-critical', ring: 'ring-risk-critical/30', label: 'Critical' },
}

const fallbackStyle = { bg: 'bg-slate-100', text: 'text-slate-500', ring: 'ring-slate-300/30', label: '—' }

export function RiskScoreBadge({
  score,
  band,
  size = 'md',
  showLabel = true,
  className,
}: RiskScoreBadgeProps) {
  const style = bandStyles[band] ?? fallbackStyle
  const { circle, score: scoreCls, label: labelCls, gap } = sizeMap[size]

  return (
    <div className={clsx('flex flex-col items-center', gap, className)}>
      <div
        className={clsx(
          'rounded-full flex items-center justify-center ring-4 shrink-0',
          'font-mono',
          circle,
          style.bg,
          style.text,
          style.ring,
          band === 'critical' && 'animate-pulse',
        )}
        aria-label={`Risk score ${score}, ${style.label} risk`}
        role="img"
      >
        <span className={scoreCls}>{Math.round(score)}</span>
      </div>
      {showLabel && size !== 'sm' && (
        <span className={clsx('font-semibold tracking-wide uppercase', labelCls, style.text)}>
          {style.label}
        </span>
      )}
    </div>
  )
}
