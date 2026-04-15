import type { RiskBand } from '@/types'

// ─── Currency ─────────────────────────────────────────────────────────────────

/**
 * Format a total rupee amount as a human-readable string.
 * formatPrice(12500000, 1200) → "₹1.5 Cr" (uses psf × area, falls back to direct amount)
 */
export function formatPrice(psf: number, area: number | null): string {
  const total = area != null ? psf * area : psf
  if (total >= 1_00_00_000) return `₹${(total / 1_00_00_000).toFixed(2)} Cr`
  if (total >= 1_00_000) return `₹${(total / 1_00_000).toFixed(2)} L`
  return `₹${total.toLocaleString('en-IN')}`
}

/**
 * Format a per-square-foot price.
 * formatPSF(8500) → "₹8,500/sqft"
 */
export function formatPSF(psf: number | null | undefined): string {
  if (psf == null) return '—'
  return `₹${psf.toLocaleString('en-IN')}/sqft`
}

/**
 * Generic compact INR formatter (used for totals in cards).
 * formatINR(12500000, true) → "₹1.3Cr"
 */
export function formatINR(amount: number | null | undefined, compact = false): string {
  if (amount == null) return '—'
  if (compact) {
    if (amount >= 1_00_00_000) return `₹${(amount / 1_00_00_000).toFixed(1)}Cr`
    if (amount >= 1_00_000) return `₹${(amount / 1_00_000).toFixed(1)}L`
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

// ─── Date ─────────────────────────────────────────────────────────────────────

/**
 * Short month-year format for possession dates.
 * formatDate("2025-12-01") → "Dec 2025"
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    month: 'short',
    year: 'numeric',
  })
}

/**
 * Full day-month-year format.
 * formatFullDate("2025-12-01") → "1 Dec 2025"
 */
export function formatFullDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/**
 * Compute delay between declared possession date and latest revised date.
 * formatDelay("2023-06-01", "2025-12-01") → "18 months delayed"
 */
export function formatDelay(
  declared: string | null | undefined,
  latest: string | null | undefined,
): string {
  if (!declared || !latest) return '—'
  const d1 = new Date(declared)
  const d2 = new Date(latest)
  const months =
    (d2.getFullYear() - d1.getFullYear()) * 12 + (d2.getMonth() - d1.getMonth())
  if (months <= 0) return 'On track'
  if (months === 1) return '1 month delayed'
  return `${months} months delayed`
}

// ─── Scores & returns ─────────────────────────────────────────────────────────

/**
 * Format a risk/quality score with one decimal.
 * formatScore(78.532) → "78.5"
 */
export function formatScore(score: number | null | undefined): string {
  if (score == null) return '—'
  return score.toFixed(1)
}

/**
 * Format a CAGR percentage with sign.
 * formatCAGR(8.5) → "+8.5% p.a."
 */
export function formatCAGR(cagr: number | null | undefined): string {
  if (cagr == null) return '—'
  const sign = cagr >= 0 ? '+' : ''
  return `${sign}${cagr.toFixed(1)}% p.a.`
}

/**
 * Format a percentage (generic).
 * formatPct(72.3) → "72.3%"
 */
export function formatPct(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${value.toFixed(1)}%`
}

// ─── Risk band utilities ──────────────────────────────────────────────────────

const RISK_COLORS: Record<RiskBand, string> = {
  low: '#15803d',
  medium: '#b45309',
  high: '#c2410c',
  critical: '#b91c1c',
}

const RISK_BG_CLASSES: Record<RiskBand, string> = {
  low: 'bg-green-50 text-green-800 border-green-200',
  medium: 'bg-amber-50 text-amber-800 border-amber-200',
  high: 'bg-orange-50 text-orange-800 border-orange-200',
  critical: 'bg-red-50 text-red-800 border-red-200',
}

const RISK_TEXT_CLASSES: Record<RiskBand, string> = {
  low: 'text-green-700',
  medium: 'text-amber-700',
  high: 'text-orange-700',
  critical: 'text-red-700',
}

const RISK_LABELS: Record<RiskBand, string> = {
  low: 'Low Risk',
  medium: 'Medium Risk',
  high: 'High Risk',
  critical: 'Critical Risk',
}

/**
 * Hex color for a risk band — use in inline styles.
 * getRiskColor('low') → '#15803d'
 */
export function getRiskColor(band: string | null | undefined): string {
  return RISK_COLORS[(band as RiskBand) ?? 'critical'] ?? '#6b7280'
}

/**
 * Human-readable label for a risk band.
 * getRiskLabel('medium') → 'Medium Risk'
 */
export function getRiskLabel(band: string | null | undefined): string {
  return RISK_LABELS[(band as RiskBand) ?? 'critical'] ?? 'Unknown'
}

/**
 * Tailwind class string for a risk badge (bg + text + border).
 * getRiskBgClass('low') → 'bg-green-50 text-green-800 border-green-200'
 */
export function getRiskBgClass(band: string | null | undefined): string {
  return RISK_BG_CLASSES[(band as RiskBand) ?? 'critical'] ?? 'bg-gray-50 text-gray-700 border-gray-200'
}

/**
 * Tailwind text-color class for a risk band.
 * getRiskTextClass('high') → 'text-orange-700'
 */
export function getRiskTextClass(band: string | null | undefined): string {
  return RISK_TEXT_CLASSES[(band as RiskBand) ?? 'critical'] ?? 'text-gray-600'
}

// ─── Legacy aliases ───────────────────────────────────────────────────────────

/** @deprecated use getRiskBgClass */
export function riskBandColor(band: RiskBand): string {
  return getRiskBgClass(band)
}

/** @deprecated use getRiskLabel */
export function riskBandLabel(band: RiskBand): string {
  return getRiskLabel(band)
}

/** @deprecated use getRiskColor with a score threshold check */
export function riskScoreColor(score: number): string {
  if (score >= 80) return RISK_TEXT_CLASSES.low
  if (score >= 60) return RISK_TEXT_CLASSES.medium
  if (score >= 40) return RISK_TEXT_CLASSES.high
  return RISK_TEXT_CLASSES.critical
}

export function projectStatusLabel(status: string | null | undefined): string {
  const map: Record<string, string> = {
    new_launch: 'New Launch',
    under_construction: 'Under Construction',
    ready_to_move: 'Ready to Move',
    completed: 'Completed',
  }
  return map[status ?? ''] ?? status ?? '—'
}

export function checklistStatusColor(status: string): string {
  return (
    ({
      pass: 'text-green-600',
      fail: 'text-red-600',
      warn: 'text-amber-500',
      pending: 'text-blue-500',
      unknown: 'text-gray-400',
    })[status] ?? 'text-gray-400'
  )
}
