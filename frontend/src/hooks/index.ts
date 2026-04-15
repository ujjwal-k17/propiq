/**
 * Hooks barrel export
 * ===================
 * import { useProjectDetail, useCuratedDeals, useSearch } from '@/hooks'
 */
export {
  useProjectDetail,
  useProjectRiskScore,
  useSearchProjects,
  useProjects,
  useProject,
  useRefreshProject,
  useComputeRisk,
  projectKeys,
} from './useProjects'

export {
  useCuratedDeals,
  useCompareProjects,
  useRiskScore,
  useRiskHistory,
  useChecklist,
  useGenerateReport,
} from './useDiligence'

export { useSearch, useSearchSuggestions } from './useSearch'

export { useAlerts } from './useAlerts'
