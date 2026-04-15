import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import {
  getProjectDetail,
  getProjectRiskScore,
  searchProjects,
  refreshProject,
} from '@/services/api'
import type { ProjectDetail, ProjectSearchParams, ProjectWithScore, RiskScore } from '@/types'

// ─── Query key factory ────────────────────────────────────────────────────────

export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (params?: ProjectSearchParams) => [...projectKeys.lists(), params ?? {}] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  riskScore: (id: string) => [...projectKeys.all, 'risk-score', id] as const,
}

// ─── useProjectDetail ─────────────────────────────────────────────────────────

/**
 * Fetch full project detail (developer, risk score, news, complaints, appreciation).
 * Cached for 10 minutes — stale in background after 5 minutes.
 */
export function useProjectDetail(id: string | null | undefined) {
  return useQuery<ProjectDetail>({
    queryKey: projectKeys.detail(id ?? ''),
    queryFn: () => getProjectDetail(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,   // 5 min
    gcTime: 10 * 60 * 1000,     // 10 min
  })
}

// ─── useProjectRiskScore ──────────────────────────────────────────────────────

/**
 * Fetch (or trigger on-demand scoring for) a project's current risk score.
 * Cached for 30 minutes — scores are expensive to regenerate.
 */
export function useProjectRiskScore(id: string | null | undefined) {
  return useQuery<RiskScore>({
    queryKey: projectKeys.riskScore(id ?? ''),
    queryFn: () => getProjectRiskScore(id!),
    enabled: !!id,
    staleTime: 30 * 60 * 1000,  // 30 min
    gcTime: 60 * 60 * 1000,     // 1 hr
    retry: false,                // Don't retry 404 (not yet scored)
  })
}

// ─── useSearchProjects ────────────────────────────────────────────────────────

/**
 * Search / list projects with filters.
 * Debouncing is the caller's responsibility (see useSearch hook).
 * Cached for 2 minutes.
 */
export function useSearchProjects(params?: ProjectSearchParams, enabled = true) {
  return useQuery<{ items: ProjectWithScore[]; total: number; page: number; size: number }>({
    queryKey: projectKeys.list(params),
    queryFn: () => searchProjects(params),
    enabled,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    placeholderData: (prev) => prev, // keep previous results while new ones load
  })
}

// ─── useProjects (alias for backward compat) ──────────────────────────────────

export function useProjects(filters?: ProjectSearchParams) {
  return useSearchProjects(filters)
}

export function useProject(id: string) {
  return useProjectDetail(id)
}

// ─── useRefreshProject ────────────────────────────────────────────────────────

export function useRefreshProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => refreshProject(projectId),
    onSuccess: (_, projectId) => {
      qc.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
      qc.invalidateQueries({ queryKey: projectKeys.riskScore(projectId) })
    },
  })
}

/** @deprecated use useRefreshProject */
export function useComputeRisk() {
  return useRefreshProject()
}
