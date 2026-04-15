/**
 * PropIQ API client
 * =================
 * Single axios instance with auth injection, error interception, and
 * fully-typed API functions that map 1-to-1 with backend route handlers.
 *
 * Import pattern:
 *   import { getProjectDetail, searchProjects } from '@/services/api'
 */
import axios, { type AxiosError, type AxiosInstance } from 'axios'

import { useAuthStore, useUIStore } from '@/store'
import type {
  AppreciationEstimate,
  ChatMessage,
  ChatResponse,
  ComparisonReport,
  CreateOrderResponse,
  CuratedDeal,
  CuratedDealsParams,
  PaginatedResponse,
  PaymentRecord,
  ProjectDetail,
  ProjectSearchParams,
  ProjectSummary,
  ProjectWithScore,
  RiskScore,
  SearchResult,
  SearchSuggestion,
  User,
  VerifyPaymentRequest,
} from '@/types'

// ─── Client setup ─────────────────────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── Request interceptor: inject Bearer token ──────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: handle 401 / 403 ───────────────────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    const status = err.response?.status
    if (status === 401) {
      useAuthStore.getState().logout()
      // Let the React Router redirect happen via the auth-protected route
    }
    if (status === 403) {
      useUIStore.getState().openUpgradeModal()
    }
    return Promise.reject(err)
  },
)

// ─── Typed helper ─────────────────────────────────────────────────────────────

function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return apiClient.get<T>(url, { params }).then((r) => r.data)
}

function post<T>(url: string, data?: unknown): Promise<T> {
  return apiClient.post<T>(url, data).then((r) => r.data)
}

function put<T>(url: string, data?: unknown): Promise<T> {
  return apiClient.put<T>(url, data).then((r) => r.data)
}

function del<T = void>(url: string): Promise<T> {
  return apiClient.delete<T>(url).then((r) => r.data)
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RegisterPayload {
  email: string
  password: string
  full_name?: string
  preferred_cities?: string[]
  risk_appetite?: string
  is_nri?: boolean
}

export function login(email: string, password: string): Promise<LoginResponse> {
  const form = new FormData()
  form.append('username', email)
  form.append('password', password)
  return apiClient
    .post<LoginResponse>('/auth/login', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export function register(data: RegisterPayload): Promise<LoginResponse> {
  return post('/auth/register', data)
}

export function getMe(): Promise<User> {
  return get('/auth/me')
}

export function updateMe(data: Partial<User>): Promise<User> {
  return put('/auth/me', data)
}

export function addToWatchlist(projectId: string): Promise<void> {
  return post(`/auth/watchlist/${projectId}`)
}

export function removeFromWatchlist(projectId: string): Promise<void> {
  return del(`/auth/watchlist/${projectId}`)
}

// ─── Projects ─────────────────────────────────────────────────────────────────

export function searchProjects(
  params?: ProjectSearchParams,
): Promise<PaginatedResponse<ProjectWithScore>> {
  return get('/projects/', params as Record<string, unknown>)
}

export function getProjectDetail(id: string): Promise<ProjectDetail> {
  return get(`/projects/${id}`)
}

export function getProjectRiskScore(id: string): Promise<RiskScore> {
  return get(`/projects/${id}/risk-score`)
}

export function refreshProject(id: string): Promise<{ status: string }> {
  return post(`/projects/${id}/refresh`)
}

export function getProjectTransactions(
  id: string,
  params?: { limit?: number; offset?: number },
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return get(`/projects/${id}/transactions`, params as Record<string, unknown>)
}

export function getProjectComplaints(
  id: string,
  params?: { limit?: number; offset?: number },
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return get(`/projects/${id}/complaints`, params as Record<string, unknown>)
}

// ─── Developers ───────────────────────────────────────────────────────────────

export function getDeveloperDetail(id: string): Promise<Record<string, unknown>> {
  return get(`/developers/${id}`)
}

export function getDeveloperProjects(
  id: string,
  params?: { limit?: number; offset?: number },
): Promise<PaginatedResponse<ProjectSummary>> {
  return get(`/developers/${id}/projects`, params as Record<string, unknown>)
}

export function searchDevelopers(
  q: string,
  params?: { city?: string; limit?: number },
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return get('/developers/search', { q, ...params })
}

// ─── Search ───────────────────────────────────────────────────────────────────

export function searchQuery(
  q: string,
  type?: 'all' | 'projects' | 'developers',
): Promise<SearchResult> {
  return get('/search', { q, type })
}

export function getSearchSuggestions(q: string): Promise<SearchSuggestion[]> {
  return get('/search/suggestions', { q })
}

// ─── Diligence ────────────────────────────────────────────────────────────────

export function getCuratedDeals(params?: CuratedDealsParams): Promise<CuratedDeal[]> {
  return get('/diligence/curated', params as Record<string, unknown>)
}

export function compareProjects(ids: string[]): Promise<ComparisonReport> {
  return get('/diligence/compare', { ids: ids.join(',') })
}

export function generateReport(projectId: string): Promise<Blob> {
  return apiClient
    .post(`/diligence/report/${projectId}`, undefined, { responseType: 'blob' })
    .then((r) => r.data as Blob)
}

export function getAppreciation(projectId: string): Promise<AppreciationEstimate> {
  return get(`/diligence/appreciation/${projectId}`)
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

export function askChat(
  message: string,
  projectId?: string,
  history?: ChatMessage[],
): Promise<ChatResponse> {
  return post('/chat/ask', {
    message,
    project_id: projectId ?? null,
    history: history ?? [],
  })
}

// ─── Payments ─────────────────────────────────────────────────────────────────

export function createPaymentOrder(
  plan: 'basic' | 'pro',
  billing_cycle: 'monthly' | 'annual',
): Promise<CreateOrderResponse> {
  return post('/payments/create-order', { plan, billing_cycle })
}

export function verifyPayment(data: VerifyPaymentRequest): Promise<User> {
  return post('/payments/verify', data)
}

export function getPaymentHistory(): Promise<PaymentRecord[]> {
  return get('/payments/history')
}

// ─── Legacy namespace exports (backward compat with existing pages) ────────────

export const authApi = {
  register: (data: RegisterPayload) => register(data),
  login: (email: string, password: string) => login(email, password),
  me: () => getMe(),
}

export const projectsApi = {
  list: (params?: ProjectSearchParams) => searchProjects(params),
  get: (id: string) => getProjectDetail(id),
  computeRisk: (id: string) => refreshProject(id),
}

export const developersApi = {
  list: (params?: { city?: string; limit?: number }) =>
    get('/developers/', params as Record<string, unknown>),
  get: (id: string) => getDeveloperDetail(id),
}

export const searchApi = {
  search: (q: string) => searchQuery(q),
  suggestions: (q: string) => getSearchSuggestions(q),
}

export const diligenceApi = {
  getRiskScore: (projectId: string) => getProjectRiskScore(projectId),
  getRiskHistory: (projectId: string) =>
    get<RiskScore[]>(`/projects/${projectId}/risk-history`),
  getChecklist: (projectId: string) =>
    get<{ project_id: string; checklist: unknown[] }>(`/diligence/checklist/${projectId}`),
  generateReport: (projectId: string) => generateReport(projectId),
}

export const chatApi = {
  ask: (projectId: string, messages: ChatMessage[]) => {
    const last = messages[messages.length - 1]
    return askChat(last?.content ?? '', projectId, messages.slice(0, -1))
  },
}
