// ─── Payments ─────────────────────────────────────────────────────────────────

export type PlanId = 'basic' | 'pro'
export type BillingCycle = 'monthly' | 'annual'
export type PaymentStatus = 'created' | 'authorized' | 'captured' | 'failed' | 'refunded'

export interface CreateOrderResponse {
  order_id: string
  amount: number        // paise
  currency: string
  key_id: string
  plan: PlanId
  billing_cycle: BillingCycle
  prefill_name: string
  prefill_email: string
}

export interface VerifyPaymentRequest {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

export interface PaymentRecord {
  id: string
  plan: PlanId
  billing_cycle: BillingCycle
  amount_paise: number
  currency: string
  status: PaymentStatus
  razorpay_order_id: string
  razorpay_payment_id: string | null
  created_at: string
}

// ─── Alerts ───────────────────────────────────────────────────────────────────

export type AlertSeverity = 'info' | 'warning' | 'critical'
export type AlertType =
  | 'rera_status_change'
  | 'new_complaint'
  | 'possession_date_delay'
  | 'construction_milestone'
  | 'risk_band_change'
  | 'developer_nclt'
  | 'developer_stress_spike'
  | 'price_change'

export interface ProjectAlert {
  id: string
  project_id: string
  project_name: string | null
  developer_id: string | null
  alert_type: AlertType
  severity: AlertSeverity
  title: string
  message: string
  payload: Record<string, unknown> | null
  created_at: string
  is_read: boolean
}

// ─── WebSocket message types ──────────────────────────────────────────────────

export interface WSConnectedPayload {
  user_id: string
  watchlist: string[]
  unread_count: number
  connected_at: string
}

export type WSMessage =
  | { type: 'connected';    data: WSConnectedPayload }
  | { type: 'alert';        data: ProjectAlert }
  | { type: 'history';      data: ProjectAlert[] }
  | { type: 'pong' }
  | { type: 'ping' }
  | { type: 'marked_read';  data: { alert_ids: string[] } }
  | { type: 'subscribed';   data: { project_ids: string[] } }
  | { type: 'error';        code: string; message: string }

// ─── Primitives ───────────────────────────────────────────────────────────────

export type RiskBand = 'low' | 'medium' | 'high' | 'critical'
export type ProjectStatus = 'new_launch' | 'under_construction' | 'ready_to_move' | 'completed'
export type ProjectType = 'residential' | 'commercial' | 'mixed'
export type SubscriptionTier = 'free' | 'basic' | 'pro' | 'enterprise'
export type RiskAppetite = 'conservative' | 'moderate' | 'aggressive'
export type OcStatus = 'not_applied' | 'applied' | 'received'
export type ReraStatus = 'active' | 'lapsed' | 'revoked' | 'completed'
export type ConfidenceLevel = 'high' | 'medium' | 'low'

// ─── User ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string | null
  subscription_tier: SubscriptionTier
  preferred_cities: string[]
  watchlist_project_ids: string[]
  risk_appetite: RiskAppetite
  // legacy compat
  plan?: SubscriptionTier
  phone?: string | null
  is_active?: boolean
  is_verified?: boolean
  reports_used_this_month?: number
  created_at?: string
}

export interface Token {
  access_token: string
  token_type: string
  expires_in?: number
  user?: User
}

// ─── Developer ────────────────────────────────────────────────────────────────

export interface Developer {
  id: string
  name: string
  city_hq: string | null
  total_projects_delivered: number
  projects_on_time_pct: number | null
  active_complaint_count: number
  financial_stress_score: number | null
  nclt_proceedings: boolean
  // extended
  legal_name?: string | null
  cin?: string | null
  pan?: string | null
  incorporation_year?: number | null
  headquarters_city?: string | null
  headquarters_state?: string | null
  website?: string | null
  description?: string | null
  total_projects?: number
  completed_projects?: number
  ongoing_projects?: number
  delayed_projects?: number
  average_delay_months?: number | null
  overall_score?: number | null
  delivery_score?: number | null
  complaint_score?: number | null
  rera_ids?: string[] | null
  last_scraped_at?: string | null
  created_at?: string
  updated_at?: string
}

/** Lightweight summary for search results / project cards */
export type DeveloperSummary = Pick<
  Developer,
  | 'id'
  | 'name'
  | 'city_hq'
  | 'total_projects_delivered'
  | 'projects_on_time_pct'
  | 'active_complaint_count'
  | 'financial_stress_score'
  | 'nclt_proceedings'
> & {
  headquarters_city?: string | null
  headquarters_state?: string | null
  total_projects?: number
  completed_projects?: number
  overall_score?: number | null
}

// ─── Risk Score ───────────────────────────────────────────────────────────────

export interface RiskScore {
  id: string
  project_id: string
  composite_score: number
  risk_band: RiskBand
  legal_score: number
  developer_score: number
  project_score: number
  location_score: number
  financial_score: number
  macro_score: number
  legal_flags: string[]
  developer_flags: string[]
  project_flags: string[]
  confidence_level: ConfidenceLevel
  appreciation_3yr_base: number | null
  appreciation_3yr_bull: number | null
  appreciation_3yr_bear: number | null
  appreciation_5yr_base: number | null
  rental_yield_estimate: number | null
  generated_at: string
  // backend field aliases for compat
  overall_score?: number
  risk_summary?: string | null
  red_flags?: string[] | null
  breakdown?: Record<string, unknown> | null
  model_version?: string
  is_current?: boolean
  computed_at?: string
}

/** Compact variant embedded in project list cards */
export interface RiskScoreBrief {
  overall_score: number
  composite_score?: number
  risk_band: RiskBand
  delay_risk_months?: number
  computed_at?: string
  generated_at?: string
}

// ─── Project ──────────────────────────────────────────────────────────────────

export interface Project {
  id: string
  name: string
  developer_id: string
  rera_registration_no: string
  city: string
  micromarket: string
  project_type: ProjectType
  total_units: number
  units_sold: number | null
  carpet_area_min: number | null
  carpet_area_max: number | null
  price_psf_min: number | null
  price_psf_max: number | null
  possession_date_declared: string | null
  possession_date_latest: string | null
  construction_pct: number | null
  oc_status: OcStatus
  rera_status: ReraStatus
  latitude: number | null
  longitude: number | null
  // additional backend fields
  developer_name?: string | null
  locality?: string | null
  status?: ProjectStatus
  rera_id?: string | null
  rera_state?: string | null
  address?: string | null
  pincode?: string | null
  state?: string
  total_towers?: number | null
  total_floors?: number | null
  bhk_types?: string[] | null
  price_per_sqft_min?: number | null
  price_per_sqft_max?: number | null
  total_price_min?: number | null
  total_price_max?: number | null
  launch_date?: string | null
  rera_possession_date?: string | null
  revised_possession_date?: string | null
  actual_completion_date?: string | null
  oc_received?: boolean
  cc_received?: boolean
  land_title_clear?: boolean | null
  total_complaints?: number
  resolved_complaints?: number
  construction_progress_pct?: number | null
  amenities?: Record<string, unknown> | null
  highlights?: string[] | null
  last_scraped_at?: string | null
  created_at?: string
  updated_at?: string
}

/** Lightweight project card used in list / search views */
export interface ProjectSummary {
  id: string
  name: string
  developer_name: string | null
  city: string
  locality: string | null
  micromarket?: string
  status?: ProjectStatus
  project_type: ProjectType
  price_per_sqft_min: number | null
  price_per_sqft_max: number | null
  price_psf_min?: number | null
  price_psf_max?: number | null
  rera_possession_date: string | null
  possession_date_latest?: string | null
  risk_score: RiskScoreBrief | null
}

export interface ProjectWithScore extends Project {
  risk_score: RiskScoreBrief | null
}

// ─── Appreciation ─────────────────────────────────────────────────────────────

export interface AppreciationEstimate {
  cagr_3yr_base: number
  cagr_3yr_bull: number
  cagr_3yr_bear: number
  cagr_5yr_base: number
  rental_yield: number
  catalysts: string[]
  risk_adjusted_return: number
  // backend aliases
  one_year_pct?: number
  three_year_pct?: number
  five_year_pct?: number
  one_year_abs?: number
  three_year_abs?: number
  five_year_abs?: number
  confidence?: ConfidenceLevel
  rationale?: string
}

// ─── Complaint ────────────────────────────────────────────────────────────────

export interface Complaint {
  id: string
  project_id: string
  complaint_id: string | null
  complainant_type: string | null
  complaint_type: string | null
  description: string | null
  status: string | null
  filed_date: string | null
  resolution_date: string | null
  penalty_amount: number | null
}

export interface ComplaintSummary {
  total: number
  resolved: number
  pending: number
  by_type: Record<string, number>
}

// ─── News ─────────────────────────────────────────────────────────────────────

export interface NewsItem {
  id: string
  project_id?: string | null
  developer_id?: string | null
  title: string
  url: string | null
  source: string | null
  published_at: string | null
  sentiment_score: number | null
  summary: string | null
}

// ─── Project Detail (full page) ───────────────────────────────────────────────

export interface ProjectDetail extends Project {
  developer: Developer
  current_risk_score: RiskScore
  recent_news: NewsItem[]
  complaint_summary: ComplaintSummary
  appreciation: AppreciationEstimate
}

// ─── Curated Deal ─────────────────────────────────────────────────────────────

export interface CuratedDeal {
  project: Project
  risk_score: RiskScore
  appreciation: AppreciationEstimate
  developer: Developer
}

// ─── Comparison ───────────────────────────────────────────────────────────────

export interface ComparisonReport {
  projects: ProjectDetail[]
  winner_id: string | null
  comparison_matrix: Record<string, Record<string, unknown>>
  summary: string
}

// ─── Search ───────────────────────────────────────────────────────────────────

export interface SearchResult {
  query: string
  projects: ProjectSummary[]
  developers: DeveloperSummary[]
  total: number
}

/** @deprecated use SearchResult */
export type SearchResults = SearchResult

/** Typeahead / autocomplete suggestion */
export interface SearchSuggestion {
  type: 'project' | 'developer' | 'city'
  id: string
  label: string
  sublabel?: string
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  response: string
  sources: string[]
  project_id: string | null
}

// ─── Checklist ────────────────────────────────────────────────────────────────

export interface ChecklistItem {
  item: string
  status: 'pass' | 'fail' | 'warn' | 'pending' | 'unknown'
  detail: string
}

// ─── API helpers ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ApiError {
  error: string
  detail: string
  request_id: string
  retry_after_seconds?: number
}

// ─── Query param shapes ───────────────────────────────────────────────────────

export interface ProjectSearchParams {
  city?: string
  project_type?: string
  status?: string
  risk_band?: RiskBand
  min_score?: number
  min_price?: number
  max_price?: number
  q?: string
  limit?: number
  offset?: number
  sort_by?: 'score' | 'price' | 'name' | 'possession_date'
  sort_dir?: 'asc' | 'desc'
}

export interface CuratedDealsParams {
  city?: string
  risk_appetite?: RiskAppetite
  limit?: number
}
