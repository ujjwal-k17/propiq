import { useState, useEffect, useRef } from 'react'
import { ChevronDown } from 'lucide-react'
import clsx from 'clsx'

export interface RiskBreakdownBarProps {
  label: string
  score: number
  weight?: number
  flags?: string[]
  className?: string
}

function scoreToColor(score: number): string {
  if (score >= 80) return '#15803d'   // risk-low
  if (score >= 60) return '#b45309'   // risk-medium
  if (score >= 40) return '#c2410c'   // risk-high
  return '#b91c1c'                    // risk-critical
}

function scoreToGradient(score: number): string {
  // Gradient blends red→green based on score
  const r = Math.round(183 - (score / 100) * (183 - 21))
  const g = Math.round(28  + (score / 100) * (128 - 28))
  const b = Math.round(28  + (score / 100) * (61  - 28))
  return `rgb(${r}, ${g}, ${b})`
}

export function RiskBreakdownBar({
  label,
  score,
  weight,
  flags = [],
  className,
}: RiskBreakdownBarProps) {
  const [expanded, setExpanded] = useState(false)
  const [animatedWidth, setAnimatedWidth] = useState(0)
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (hasAnimated.current) return
    hasAnimated.current = true
    const raf = requestAnimationFrame(() => {
      setTimeout(() => setAnimatedWidth(score), 50)
    })
    return () => cancelAnimationFrame(raf)
  }, [score])

  const hasFlags = flags.length > 0
  const color = scoreToGradient(score)

  return (
    <div className={clsx('space-y-2', className)}>
      <div
        className={clsx(
          'flex items-center gap-3',
          hasFlags && 'cursor-pointer group',
        )}
        onClick={() => hasFlags && setExpanded((x) => !x)}
        role={hasFlags ? 'button' : undefined}
        tabIndex={hasFlags ? 0 : undefined}
        aria-expanded={hasFlags ? expanded : undefined}
        onKeyDown={(e) => {
          if (hasFlags && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault()
            setExpanded((x) => !x)
          }
        }}
      >
        {/* Label */}
        <span className="w-44 text-sm text-slate-600 shrink-0 font-medium truncate group-hover:text-propiq-navy transition-colors">
          {label}
        </span>

        {/* Progress bar */}
        <div
          className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden"
          aria-label={`${label}: ${score} out of 100`}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{ width: `${animatedWidth}%`, backgroundColor: color }}
          />
        </div>

        {/* Score + weight */}
        <div className="flex items-center gap-2 shrink-0 w-20 justify-end">
          <span className="font-mono font-bold text-sm" style={{ color }}>
            {score}
          </span>
          {weight != null && (
            <span className="text-2xs text-slate-400">({weight}%)</span>
          )}
          {hasFlags && (
            <ChevronDown
              size={14}
              className={clsx(
                'text-slate-400 transition-transform duration-200',
                expanded && 'rotate-180',
              )}
            />
          )}
        </div>
      </div>

      {/* Flags list */}
      {hasFlags && expanded && (
        <ul
          className="ml-[11.5rem] space-y-1 animate-fade-in"
          aria-label={`${label} risk flags`}
        >
          {flags.map((flag, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-xs text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-1.5"
            >
              <span aria-hidden="true" className="mt-0.5 shrink-0">⚠</span>
              {flag}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
