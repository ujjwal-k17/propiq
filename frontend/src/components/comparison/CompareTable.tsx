import { Trophy, TrendingUp, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import type { ProjectDetail } from '@/types'
import { RiskScoreBadge } from '@/components/ui/RiskScoreBadge'
import { RiskBreakdownBar } from '@/components/ui/RiskBreakdownBar'
import { formatPSF, formatDate, formatCAGR, formatDelay } from '@/utils/formatters'

export interface CompareTableProps {
  projects: ProjectDetail[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Index of the project with the highest value (numerically best) */
function bestIdx(values: (number | null | undefined)[], higherIsBetter = true): number {
  const valid = values.map((v) => (v == null ? -Infinity : higherIsBetter ? v : -v))
  const max = Math.max(...valid)
  return valid.indexOf(max)
}

function bestPSFIdx(values: (number | null | undefined)[]): number {
  // Lower price per sqft is NOT automatically better — this is more nuanced,
  // but for comparison we highlight the lowest psf (most affordable)
  const valid = values.map((v) => (v == null ? Infinity : v))
  return valid.indexOf(Math.min(...valid))
}

function Cell({
  children,
  highlight = false,
  className,
}: {
  children: React.ReactNode
  highlight?: boolean
  className?: string
}) {
  return (
    <td
      className={clsx(
        'px-4 py-3 text-sm text-center border-b border-slate-50 transition-colors',
        highlight ? 'bg-green-50 font-semibold' : 'bg-white',
        className,
      )}
    >
      {children}
    </td>
  )
}

function RowLabel({ children }: { children: React.ReactNode }) {
  return (
    <td className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-50 w-40 border-b border-slate-100 whitespace-nowrap">
      {children}
    </td>
  )
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <tr>
      <td
        colSpan={100}
        className="px-4 py-2 text-xs font-bold text-propiq-navy bg-navy-50 uppercase tracking-widest border-b border-navy-100"
      >
        {children}
      </td>
    </tr>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function CompareTable({ projects }: CompareTableProps) {
  if (projects.length < 2) return null

  const scores = projects.map((p) => p.current_risk_score?.composite_score ?? p.current_risk_score?.overall_score ?? 0)
  const legalScores = projects.map((p) => p.current_risk_score?.legal_score ?? 0)
  const devScores   = projects.map((p) => p.current_risk_score?.developer_score ?? 0)
  const projScores  = projects.map((p) => p.current_risk_score?.project_score ?? 0)
  const locScores   = projects.map((p) => p.current_risk_score?.location_score ?? 0)
  const finScores   = projects.map((p) => p.current_risk_score?.financial_score ?? 0)
  const cagr3 = projects.map((p) => p.appreciation?.cagr_3yr_base ?? null)
  const cagr5 = projects.map((p) => p.appreciation?.cagr_5yr_base ?? null)
  const rental = projects.map((p) => p.appreciation?.rental_yield ?? null)
  const minPSF = projects.map((p) => p.price_psf_min ?? p.price_per_sqft_min ?? null)
  const complaints = projects.map((p) => p.complaint_summary?.total ?? p.total_complaints ?? 0)
  const construction = projects.map((p) => p.construction_pct ?? p.construction_progress_pct ?? null)

  const overallWinner = bestIdx(scores)
  const scoreWinner   = overallWinner

  // "Best for investors" heuristic: highest risk-adjusted return from appreciation
  const riskAdjusted = projects.map((p) => p.appreciation?.risk_adjusted_return ?? null)
  const investorWinner = bestIdx(riskAdjusted)

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-100 shadow-card">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-propiq-navy">
            <th className="px-4 py-4 text-left text-xs font-semibold text-white/70 uppercase tracking-wide w-40">
              Comparison
            </th>
            {projects.map((p, i) => (
              <th key={p.id} className="px-4 py-4 text-center">
                <div className="flex flex-col items-center gap-1">
                  {i === overallWinner && (
                    <span className="inline-flex items-center gap-1 text-2xs bg-white/20 text-white rounded-full px-2 py-0.5 font-medium mb-1">
                      <Trophy size={9} /> Top Pick
                    </span>
                  )}
                  <p className="text-sm font-semibold text-white leading-snug max-w-[140px] text-center">
                    {p.name}
                  </p>
                  <p className="text-2xs text-white/60">{p.developer?.name ?? p.developer_name}</p>
                </div>
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {/* ── Risk Scores ── */}
          <SectionHeader>Risk Assessment</SectionHeader>
          <tr>
            <RowLabel>Overall Score</RowLabel>
            {projects.map((p, i) => {
              const rs = p.current_risk_score
              const s = rs?.composite_score ?? rs?.overall_score ?? 0
              return (
                <Cell key={p.id} highlight={i === scoreWinner}>
                  <div className="flex justify-center">
                    <RiskScoreBadge score={s} band={rs?.risk_band ?? 'critical'} size="md" />
                  </div>
                </Cell>
              )
            })}
          </tr>

          {/* Dimension scores */}
          {[
            { label: 'Legal & Compliance',  values: legalScores, idx: bestIdx(legalScores) },
            { label: 'Developer Track Record', values: devScores, idx: bestIdx(devScores) },
            { label: 'Project Health',       values: projScores, idx: bestIdx(projScores) },
            { label: 'Location Quality',     values: locScores,  idx: bestIdx(locScores) },
            { label: 'Financial Indicators', values: finScores,  idx: bestIdx(finScores) },
          ].map(({ label, values, idx }) => (
            <tr key={label}>
              <RowLabel>{label}</RowLabel>
              {projects.map((p, i) => (
                <Cell key={p.id} highlight={i === idx}>
                  <div className="flex justify-center">
                    <ScorePill score={values[i] ?? 0} />
                  </div>
                </Cell>
              ))}
            </tr>
          ))}

          {/* ── Project Details ── */}
          <SectionHeader>Project Details</SectionHeader>
          <tr>
            <RowLabel>RERA Status</RowLabel>
            {projects.map((p) => (
              <Cell key={p.id}>
                <span className={clsx(
                  'text-xs font-medium px-2 py-0.5 rounded-full border',
                  p.rera_status === 'active'
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : 'bg-red-50 text-red-700 border-red-200',
                )}>
                  {(p.rera_status ?? 'unknown').toUpperCase()}
                </span>
              </Cell>
            ))}
          </tr>
          <tr>
            <RowLabel>Price / sqft</RowLabel>
            {projects.map((p, i) => (
              <Cell key={p.id} highlight={i === bestPSFIdx(minPSF)}>
                <span className="font-mono text-propiq-navy">
                  {formatPSF(minPSF[i])}
                </span>
              </Cell>
            ))}
          </tr>
          <tr>
            <RowLabel>Possession Date</RowLabel>
            {projects.map((p) => {
              const date = p.possession_date_latest ?? p.revised_possession_date ?? p.possession_date_declared ?? p.rera_possession_date
              const declared = p.possession_date_declared ?? p.rera_possession_date
              const latest   = p.possession_date_latest ?? p.revised_possession_date
              const delay    = declared && latest ? formatDelay(declared, latest) : null
              const isDelayed = delay && delay !== 'On track'
              return (
                <Cell key={p.id}>
                  <p className="text-xs font-medium">{formatDate(date)}</p>
                  {isDelayed && (
                    <p className="text-2xs text-risk-medium flex items-center justify-center gap-0.5 mt-0.5">
                      <AlertTriangle size={9} /> {delay}
                    </p>
                  )}
                </Cell>
              )
            })}
          </tr>
          <tr>
            <RowLabel>Construction</RowLabel>
            {projects.map((p, i) => {
              const pct = construction[i]
              return (
                <Cell key={p.id} highlight={pct != null && i === bestIdx(construction)}>
                  {pct != null ? (
                    <div className="flex flex-col items-center gap-1">
                      <span className="font-mono text-sm font-bold text-propiq-navy">{Math.round(pct)}%</span>
                      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-propiq-gradient"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  ) : '—'}
                </Cell>
              )
            })}
          </tr>
          <tr>
            <RowLabel>Complaints</RowLabel>
            {projects.map((p, i) => (
              <Cell key={p.id} highlight={i === bestIdx(complaints, false)}>
                <span className={clsx(
                  'font-mono font-bold',
                  complaints[i] === 0 ? 'text-risk-low' : complaints[i] < 5 ? 'text-risk-medium' : 'text-risk-critical',
                )}>
                  {complaints[i]}
                </span>
              </Cell>
            ))}
          </tr>

          {/* ── Returns ── */}
          <SectionHeader>Appreciation Forecast</SectionHeader>
          {[
            { label: '3-Year CAGR (Base)', values: cagr3, idx: bestIdx(cagr3) },
            { label: '5-Year CAGR (Base)', values: cagr5, idx: bestIdx(cagr5) },
            { label: 'Rental Yield',       values: rental, idx: bestIdx(rental) },
          ].map(({ label, values, idx }) => (
            <tr key={label}>
              <RowLabel>{label}</RowLabel>
              {projects.map((p, i) => (
                <Cell key={p.id} highlight={i === idx}>
                  <span className={clsx(
                    'font-mono font-semibold text-sm',
                    i === idx ? 'text-risk-low' : 'text-slate-600',
                  )}>
                    {formatCAGR(values[i])}
                  </span>
                </Cell>
              ))}
            </tr>
          ))}

          {/* ── Verdict ── */}
          <tr className="bg-slate-50">
            <td className="px-4 py-5 text-xs font-bold text-propiq-navy uppercase tracking-wide whitespace-nowrap">
              <div className="flex items-center gap-1.5">
                <TrendingUp size={14} />
                Best for Investors
              </div>
            </td>
            {projects.map((p, i) => (
              <td key={p.id} className={clsx('px-4 py-5 text-center border-t-2', i === investorWinner ? 'border-propiq-teal bg-teal-50' : 'border-transparent')}>
                {i === investorWinner ? (
                  <div className="flex flex-col items-center gap-2">
                    <Trophy size={20} className="text-propiq-teal" />
                    <span className="text-xs font-semibold text-propiq-teal">Recommended</span>
                    <p className="text-2xs text-slate-500 max-w-[120px]">
                      Best risk-adjusted return among compared projects
                    </p>
                  </div>
                ) : (
                  <span className="text-xs text-slate-400">—</span>
                )}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function ScorePill({ score }: { score: number }) {
  const color =
    score >= 80 ? '#15803d' : score >= 60 ? '#b45309' : score >= 40 ? '#c2410c' : '#b91c1c'
  return (
    <span
      className="font-mono font-bold text-sm px-2.5 py-0.5 rounded-full"
      style={{ color, backgroundColor: `${color}18` }}
    >
      {Math.round(score)}
    </span>
  )
}
