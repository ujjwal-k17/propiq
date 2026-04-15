import { useState } from 'react'
import { ChevronDown, X, SlidersHorizontal } from 'lucide-react'
import clsx from 'clsx'
import type { RiskBand, ProjectType, RiskAppetite } from '@/types'
import { Button } from '@/components/ui/Button'

export interface FilterValues {
  cities: string[]
  riskBands: RiskBand[]
  projectType: ProjectType | ''
  maxPricePSF: number
  minPricePSF: number
  possessionBefore: string
}

const DEFAULT_FILTERS: FilterValues = {
  cities: [],
  riskBands: [],
  projectType: '',
  maxPricePSF: 30000,
  minPricePSF: 2000,
  possessionBefore: '',
}

const CITIES = ['Mumbai', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Noida', 'Gurugram', 'Navi Mumbai']
const RISK_BANDS: { value: RiskBand; label: string; color: string }[] = [
  { value: 'low',      label: 'Low Risk',      color: 'bg-risk-low' },
  { value: 'medium',   label: 'Medium Risk',   color: 'bg-risk-medium' },
  { value: 'high',     label: 'High Risk',     color: 'bg-risk-high' },
  { value: 'critical', label: 'Critical Risk', color: 'bg-risk-critical' },
]

export interface FilterPanelProps {
  filters: FilterValues
  onChange: (filters: FilterValues) => void
  className?: string
}

function activeFilterCount(f: FilterValues): number {
  return (
    f.cities.length +
    f.riskBands.length +
    (f.projectType ? 1 : 0) +
    (f.possessionBefore ? 1 : 0) +
    (f.minPricePSF > 2000 || f.maxPricePSF < 30000 ? 1 : 0)
  )
}

export function FilterPanel({ filters, onChange, className }: FilterPanelProps) {
  const [open, setOpen] = useState(false)
  const count = activeFilterCount(filters)

  function toggle<K extends keyof FilterValues>(key: K, value: FilterValues[K] extends (infer U)[] ? U : never) {
    const arr = filters[key] as string[]
    onChange({
      ...filters,
      [key]: arr.includes(value as string)
        ? arr.filter((x) => x !== value)
        : [...arr, value],
    })
  }

  const reset = () => onChange(DEFAULT_FILTERS)

  return (
    <div className={clsx('bg-white rounded-2xl border border-slate-100 shadow-card', className)}>
      {/* Header */}
      <button
        onClick={() => setOpen((x) => !x)}
        className="w-full flex items-center justify-between p-4 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 font-semibold text-propiq-navy">
          <SlidersHorizontal size={16} />
          Filters
          {count > 0 && (
            <span className="ml-1 text-xs bg-propiq-blue text-white rounded-full w-5 h-5 inline-flex items-center justify-center font-bold">
              {count}
            </span>
          )}
        </span>
        <div className="flex items-center gap-2">
          {count > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); reset() }}
              className="text-xs text-slate-400 hover:text-red-500 flex items-center gap-1 transition-colors"
              aria-label="Clear all filters"
            >
              <X size={12} /> Clear all
            </button>
          )}
          <ChevronDown
            size={16}
            className={clsx('text-slate-400 transition-transform duration-200', open && 'rotate-180')}
          />
        </div>
      </button>

      {open && (
        <div className="px-4 pb-5 space-y-5 border-t border-slate-50">
          {/* City */}
          <FilterSection label="City">
            <div className="flex flex-wrap gap-2">
              {CITIES.map((city) => (
                <FilterChip
                  key={city}
                  label={city}
                  selected={filters.cities.includes(city)}
                  onClick={() => toggle('cities', city as never)}
                />
              ))}
            </div>
          </FilterSection>

          {/* Risk Level */}
          <FilterSection label="Risk Level">
            <div className="space-y-2">
              {RISK_BANDS.map(({ value, label, color }) => (
                <label key={value} className="flex items-center gap-2.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={filters.riskBands.includes(value)}
                    onChange={() => toggle('riskBands', value as never)}
                    className="w-4 h-4 rounded border-slate-300 text-propiq-blue focus:ring-propiq-blue"
                  />
                  <span className={clsx('w-2.5 h-2.5 rounded-full shrink-0', color)} />
                  <span className="text-sm text-slate-700 group-hover:text-propiq-navy transition-colors">
                    {label}
                  </span>
                </label>
              ))}
            </div>
          </FilterSection>

          {/* Property Type */}
          <FilterSection label="Property Type">
            <div className="flex gap-2">
              {(['', 'residential', 'commercial'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => onChange({ ...filters, projectType: t as ProjectType | '' })}
                  className={clsx(
                    'px-3 py-1.5 text-sm rounded-lg border font-medium transition-all',
                    filters.projectType === t
                      ? 'bg-propiq-navy text-white border-propiq-navy'
                      : 'border-slate-200 text-slate-600 hover:border-propiq-blue hover:text-propiq-blue',
                  )}
                >
                  {t === '' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </FilterSection>

          {/* Price Range */}
          <FilterSection label={`Price / sqft: ₹${(filters.minPricePSF / 1000).toFixed(0)}K – ₹${(filters.maxPricePSF / 1000).toFixed(0)}K`}>
            <div className="space-y-2 px-1">
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-8">Min</span>
                <input
                  type="range"
                  min={2000}
                  max={filters.maxPricePSF - 1000}
                  step={500}
                  value={filters.minPricePSF}
                  onChange={(e) => onChange({ ...filters, minPricePSF: Number(e.target.value) })}
                  className="flex-1 h-1.5 accent-propiq-blue"
                  aria-label="Minimum price per sqft"
                />
                <span className="text-xs font-mono text-propiq-navy w-14 text-right">
                  ₹{(filters.minPricePSF / 1000).toFixed(0)}K
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-8">Max</span>
                <input
                  type="range"
                  min={filters.minPricePSF + 1000}
                  max={30000}
                  step={500}
                  value={filters.maxPricePSF}
                  onChange={(e) => onChange({ ...filters, maxPricePSF: Number(e.target.value) })}
                  className="flex-1 h-1.5 accent-propiq-blue"
                  aria-label="Maximum price per sqft"
                />
                <span className="text-xs font-mono text-propiq-navy w-14 text-right">
                  ₹{(filters.maxPricePSF / 1000).toFixed(0)}K
                </span>
              </div>
            </div>
          </FilterSection>

          {/* Possession before */}
          <FilterSection label="Possession Before">
            <input
              type="date"
              value={filters.possessionBefore}
              onChange={(e) => onChange({ ...filters, possessionBefore: e.target.value })}
              className="text-sm border border-slate-200 rounded-lg px-3 py-2 text-slate-700 focus:outline-none focus:ring-2 focus:ring-propiq-blue/30 focus:border-propiq-blue w-full"
              aria-label="Possession before date"
            />
          </FilterSection>
        </div>
      )}
    </div>
  )
}

function FilterSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="pt-4 space-y-2.5">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
      {children}
    </div>
  )
}

function FilterChip({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-2.5 py-1 text-xs rounded-full border font-medium transition-all',
        selected
          ? 'bg-propiq-navy text-white border-propiq-navy'
          : 'border-slate-200 text-slate-600 hover:border-propiq-blue hover:text-propiq-blue',
      )}
    >
      {label}
    </button>
  )
}

export { DEFAULT_FILTERS }
