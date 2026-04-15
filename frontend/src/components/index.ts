// ── Gating / upgrade ─────────────────────────────────────────────────────────
export { UpgradeGate }        from './ui/UpgradeGate'
export { UpgradeModal }       from './ui/UpgradeModal'
export type { UpgradeGateProps } from './ui/UpgradeGate'

// ── UI primitives ─────────────────────────────────────────────────────────────
export { Button }             from './ui/Button'
export { Badge }              from './ui/Badge'
export { Card }               from './ui/Card'
export { Skeleton, ProjectCardSkeleton, ListItemSkeleton } from './ui/Skeleton'
export { Input }              from './ui/Input'
export { Modal }              from './ui/Modal'
export { RiskScoreBadge }     from './ui/RiskScoreBadge'
export { RiskBreakdownBar }   from './ui/RiskBreakdownBar'
export { ScoreGauge }         from './ui/ScoreGauge'
export { AppreciationCard }   from './ui/AppreciationCard'

// ── Project ───────────────────────────────────────────────────────────────────
export { ProjectCard }        from './project/ProjectCard'
export { ProjectListItem }    from './project/ProjectListItem'

// ── Developer ─────────────────────────────────────────────────────────────────
export { DeveloperCard }      from './developer/DeveloperCard'

// ── Search ────────────────────────────────────────────────────────────────────
export { SearchBar }          from './search/SearchBar'
export { FilterPanel, DEFAULT_FILTERS } from './search/FilterPanel'

// ── Layout ────────────────────────────────────────────────────────────────────
export { Navbar }             from './layout/Navbar'
export { Footer }             from './layout/Footer'

// ── Chat ──────────────────────────────────────────────────────────────────────
export { ChatInterface }      from './chat/ChatInterface'

// ── Auth ──────────────────────────────────────────────────────────────────────
export { AuthModal }          from './auth/AuthModal'

// ── Comparison ────────────────────────────────────────────────────────────────
export { CompareTable }       from './comparison/CompareTable'

// ── Map ───────────────────────────────────────────────────────────────────────
export { ProjectMap }         from './map/ProjectMap'
export type { ProjectMapProps, POI } from './map/ProjectMap'

// ── Alerts ────────────────────────────────────────────────────────────────────
export { AlertBell }          from './alerts/AlertBell'
export { AlertPanel }         from './alerts/AlertPanel'
export type { AlertBellProps } from './alerts/AlertBell'
export type { AlertPanelProps } from './alerts/AlertPanel'

// ── Prop types (re-exported for convenience) ──────────────────────────────────
export type { ButtonProps }        from './ui/Button'
export type { BadgeProps }         from './ui/Badge'
export type { CardProps }          from './ui/Card'
export type { InputProps }         from './ui/Input'
export type { ModalProps }         from './ui/Modal'
export type { RiskScoreBadgeProps } from './ui/RiskScoreBadge'
export type { RiskBreakdownBarProps } from './ui/RiskBreakdownBar'
export type { ScoreGaugeProps }    from './ui/ScoreGauge'
export type { AppreciationCardProps } from './ui/AppreciationCard'
export type { ProjectCardProps }   from './project/ProjectCard'
export type { ProjectListItemProps } from './project/ProjectListItem'
export type { DeveloperCardProps } from './developer/DeveloperCard'
export type { SearchBarProps }     from './search/SearchBar'
export type { FilterPanelProps, FilterValues } from './search/FilterPanel'
export type { ChatInterfaceProps } from './chat/ChatInterface'
export type { CompareTableProps }  from './comparison/CompareTable'
