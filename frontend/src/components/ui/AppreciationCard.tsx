import { TrendingUp, Home } from 'lucide-react'
import clsx from 'clsx'
import type { AppreciationEstimate } from '@/types'
import { formatCAGR } from '@/utils/formatters'

export interface AppreciationCardProps {
  appreciation: AppreciationEstimate
  className?: string
}

interface ScenarioColProps {
  label: string
  cagr: number
  color: 'base' | 'bull' | 'bear'
}

const colorMap = {
  base: { heading: 'text-propiq-blue',  value: 'text-propiq-blue',  bg: 'bg-blue-50',  border: 'border-blue-100' },
  bull: { heading: 'text-risk-low',     value: 'text-risk-low',     bg: 'bg-green-50', border: 'border-green-100' },
  bear: { heading: 'text-risk-critical', value: 'text-risk-critical', bg: 'bg-red-50',  border: 'border-red-100' },
}

function ScenarioCol({ label, cagr, color }: ScenarioColProps) {
  const c = colorMap[color]
  return (
    <div className={clsx('rounded-xl p-3 border text-center', c.bg, c.border)}>
      <p className={clsx('text-2xs font-semibold uppercase tracking-wide mb-1', c.heading)}>
        {label}
      </p>
      <p className={clsx('font-mono font-bold text-base', c.value)}>
        {formatCAGR(cagr)}
      </p>
    </div>
  )
}

export function AppreciationCard({ appreciation, className }: AppreciationCardProps) {
  const {
    cagr_3yr_base,
    cagr_3yr_bull,
    cagr_3yr_bear,
    cagr_5yr_base,
    rental_yield,
    catalysts,
    risk_adjusted_return,
  } = appreciation

  return (
    <div className={clsx('space-y-5', className)}>
      {/* 3-Year Forecast */}
      <div>
        <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
          <TrendingUp size={14} className="text-propiq-teal" />
          3-Year Price Appreciation
        </h4>
        <div className="grid grid-cols-3 gap-2">
          <ScenarioCol label="Bear" cagr={cagr_3yr_bear} color="bear" />
          <ScenarioCol label="Base" cagr={cagr_3yr_base} color="base" />
          <ScenarioCol label="Bull" cagr={cagr_3yr_bull} color="bull" />
        </div>
      </div>

      {/* 5-Year + Rental */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-slate-100 p-3 text-center bg-slate-50">
          <p className="text-2xs text-slate-500 font-semibold uppercase tracking-wide mb-1">
            5-Year CAGR (Base)
          </p>
          <p className="font-mono font-bold text-base text-propiq-navy">
            {formatCAGR(cagr_5yr_base)}
          </p>
        </div>
        <div className="rounded-xl border border-teal-100 p-3 text-center bg-teal-50">
          <p className="text-2xs text-propiq-teal font-semibold uppercase tracking-wide mb-1 flex items-center justify-center gap-1">
            <Home size={10} /> Rental Yield
          </p>
          <p className="font-mono font-bold text-base text-propiq-teal">
            {formatCAGR(rental_yield)}
          </p>
        </div>
      </div>

      {/* Risk-adjusted return */}
      <div className="flex items-center justify-between bg-navy-50 border border-navy-100 rounded-xl px-4 py-3">
        <span className="text-sm text-slate-600 font-medium">Risk-adjusted return</span>
        <span className="font-mono font-bold text-propiq-navy">{formatCAGR(risk_adjusted_return)}</span>
      </div>

      {/* Catalysts */}
      {catalysts.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 font-medium mb-2">Growth Catalysts</p>
          <div className="flex flex-wrap gap-1.5">
            {catalysts.map((c) => (
              <span
                key={c}
                className="inline-flex items-center text-xs bg-teal-50 text-propiq-teal border border-teal-100 rounded-full px-2.5 py-0.5 font-medium"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
