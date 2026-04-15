import { useQuery, useMutation } from '@tanstack/react-query'

import {
  getCuratedDeals,
  compareProjects,
  generateReport,
  getProjectRiskScore,
} from '@/services/api'
import { diligenceApi } from '@/services/api'
import type { ChecklistItem, CuratedDeal, CuratedDealsParams, RiskScore } from '@/types'

// ─── useCuratedDeals ──────────────────────────────────────────────────────────

/**
 * Fetch PropIQ curated deals with optional city / risk_appetite filter.
 * Cached 15 minutes — list changes infrequently.
 */
export function useCuratedDeals(params?: CuratedDealsParams) {
  return useQuery<CuratedDeal[]>({
    queryKey: ['diligence', 'curated', params ?? {}],
    queryFn: () => getCuratedDeals(params),
    staleTime: 15 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  })
}

// ─── useCompareProjects ───────────────────────────────────────────────────────

export function useCompareProjects(ids: string[]) {
  return useQuery({
    queryKey: ['diligence', 'compare', [...ids].sort()],
    queryFn: () => compareProjects(ids),
    enabled: ids.length >= 2 && ids.length <= 3,
    staleTime: 10 * 60 * 1000,
  })
}

// ─── useRiskScore (diligence view) ────────────────────────────────────────────

export function useRiskScore(projectId: string | null | undefined) {
  return useQuery<RiskScore>({
    queryKey: ['risk-score', projectId ?? ''],
    queryFn: () => getProjectRiskScore(projectId!),
    enabled: !!projectId,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: false,
  })
}

// ─── useRiskHistory ───────────────────────────────────────────────────────────

export function useRiskHistory(projectId: string | null | undefined) {
  return useQuery<RiskScore[]>({
    queryKey: ['risk-history', projectId ?? ''],
    queryFn: () => diligenceApi.getRiskHistory(projectId!),
    enabled: !!projectId,
    staleTime: 15 * 60 * 1000,
  })
}

// ─── useChecklist ─────────────────────────────────────────────────────────────

export function useChecklist(projectId: string | null | undefined) {
  return useQuery<{ project_id: string; checklist: ChecklistItem[] }>({
    queryKey: ['checklist', projectId ?? ''],
    queryFn: () => diligenceApi.getChecklist(projectId!),
    enabled: !!projectId,
    staleTime: 10 * 60 * 1000,
  })
}

// ─── useGenerateReport ────────────────────────────────────────────────────────

export function useGenerateReport() {
  return useMutation({
    mutationFn: (projectId: string) => generateReport(projectId),
    onSuccess: (blob, projectId) => {
      // Trigger browser download
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `propiq-report-${projectId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}
