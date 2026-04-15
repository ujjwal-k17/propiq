import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LayoutGrid, List, SlidersHorizontal, ChevronRight } from 'lucide-react'
import { useCuratedDeals, useSearchProjects } from '@/hooks'
import { useAuthStore } from '@/store'
import {
  ProjectCard, ProjectListItem, FilterPanel, ProjectCardSkeleton,
  ListItemSkeleton, Button,
} from '@/components'
import { DEFAULT_FILTERS, type FilterValues } from '@/components/search/FilterPanel'
import type { ProjectSearchParams, RiskBand } from '@/types'

type ViewMode = 'grid' | 'list'

const CITIES = ['Mumbai', 'Bengaluru', 'Pune', 'Hyderabad', 'Delhi NCR']
const PAGE_SIZE = 18

const CURATED_SECTIONS = [
  { label: 'Best Risk/Return', sort: 'score' as const,  city: undefined },
  { label: 'Lowest Entry Price', sort: 'price' as const, city: undefined },
  { label: 'Soonest Possession', sort: 'possession_date' as const, city: undefined },
]

export function DiscoverPage() {
  const { user } = useAuthStore()
  const [view, setView] = useState<ViewMode>('grid')
  const [filters, setFilters] = useState<FilterValues>(DEFAULT_FILTERS)
  const [sort, setSort] = useState<ProjectSearchParams['sort_by']>('score')
  const [page, setPage] = useState(0)
  const [mobileFilters, setMobileFilters] = useState(false)
  const [activeCity, setActiveCity] = useState<string | undefined>(
    user?.preferred_cities?.[0],
  )

  useEffect(() => { document.title = 'Discover Projects — PropIQ' }, [])
  useEffect(() => { setPage(0) }, [filters, sort, activeCity])

  const params: ProjectSearchParams = {
    city: activeCity ?? (filters.cities.length === 1 ? filters.cities[0] : undefined),
    risk_band: filters.riskBands.length === 1 ? (filters.riskBands[0] as RiskBand) : undefined,
    project_type: filters.projectType || undefined,
    min_price: filters.minPricePSF > 2000 ? filters.minPricePSF : undefined,
    max_price: filters.maxPricePSF < 30000 ? filters.maxPricePSF : undefined,
    sort_by: sort,
    sort_dir: sort === 'price' ? 'asc' : 'desc',
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  }

  const { data, isLoading } = useSearchProjects(params, true)
  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  // Curated sections (only on page 0 with no filters active)
  const filtersActive = Object.values(filters).some(
    (v) => (Array.isArray(v) ? v.length > 0 : !!v),
  )
  const showCurated = page === 0 && !filtersActive

  const curatedParams: Parameters<typeof useCuratedDeals>[0] = {
    city: activeCity,
    limit: 6,
  }
  const { data: featured = [] } = useCuratedDeals(curatedParams)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-propiq-navy">Discover Projects</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {!isLoading && total > 0
            ? `${total.toLocaleString('en-IN')} projects across India`
            : 'Browse top-rated projects'}
        </p>
      </div>

      {/* City filter tabs */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {[undefined, ...CITIES].map((city) => (
          <button
            key={city ?? 'all'}
            onClick={() => setActiveCity(city)}
            className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all ${
              activeCity === city
                ? 'bg-propiq-navy text-white border-propiq-navy'
                : 'border-slate-200 text-slate-600 hover:border-propiq-blue'
            }`}
          >
            {city ?? 'All India'}
          </button>
        ))}
      </div>

      <div className="flex gap-6 items-start">
        {/* Filter sidebar (desktop) */}
        <aside className="hidden lg:block w-72 shrink-0">
          <FilterPanel filters={filters} onChange={setFilters} />
        </aside>

        <div className="flex-1 min-w-0">
          {/* Toolbar */}
          <div className="flex items-center justify-between mb-4 gap-3">
            <button
              onClick={() => setMobileFilters(true)}
              className="lg:hidden flex items-center gap-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-xl px-3 py-2 hover:bg-slate-50"
            >
              <SlidersHorizontal size={14} /> Filters
              {filtersActive && (
                <span className="w-4 h-4 bg-propiq-blue text-white rounded-full text-2xs font-bold flex items-center justify-center">!</span>
              )}
            </button>

            <div className="flex items-center gap-2 ml-auto">
              {/* Sort */}
              <span className="text-xs text-slate-500 hidden sm:block">Sort:</span>
              {([
                { value: 'score',           label: 'Most Safe' },
                { value: 'possession_date', label: 'Best Appreciation' },
                { value: 'price',           label: 'Lowest Price' },
              ] as { value: NonNullable<ProjectSearchParams['sort_by']>; label: string }[]).map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setSort(value)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                    sort === value
                      ? 'bg-propiq-navy text-white border-propiq-navy'
                      : 'border-slate-200 text-slate-600 hover:border-propiq-blue'
                  }`}
                >
                  {label}
                </button>
              ))}

              {/* View toggle */}
              <div className="flex border border-slate-200 rounded-lg overflow-hidden ml-1">
                {(['grid', 'list'] as ViewMode[]).map((v) => (
                  <button
                    key={v}
                    onClick={() => setView(v)}
                    className={`p-2 transition-colors ${
                      view === v ? 'bg-propiq-navy text-white' : 'text-slate-400 hover:bg-slate-50'
                    }`}
                    aria-label={v === 'grid' ? 'Grid view' : 'List view'}
                  >
                    {v === 'grid' ? <LayoutGrid size={14} /> : <List size={14} />}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Curated featured section (shown only when no filters active) */}
          {showCurated && featured.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-propiq-navy uppercase tracking-wider">
                  PropIQ Picks
                </h2>
                <Link
                  to="/search?q="
                  className="text-xs text-propiq-blue hover:underline flex items-center gap-0.5"
                >
                  View all <ChevronRight size={12} />
                </Link>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {featured.slice(0, 3).map((deal) => (
                  <ProjectCard
                    key={deal.project.id}
                    project={deal.project}
                    riskScore={deal.risk_score}
                  />
                ))}
              </div>
              <div className="border-t border-slate-200 mt-8 mb-6" />
            </div>
          )}

          {/* Results */}
          {isLoading ? (
            view === 'grid' ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(9)].map((_, i) => <ProjectCardSkeleton key={i} />)}
              </div>
            ) : (
              <div className="space-y-3">
                {[...Array(8)].map((_, i) => <ListItemSkeleton key={i} />)}
              </div>
            )
          ) : items.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-4xl mb-4">🔍</p>
              <h3 className="font-semibold text-propiq-navy mb-1">No projects match your filters</h3>
              <p className="text-sm text-slate-500 mb-4">Try adjusting your filters or selecting a different city.</p>
              <Button variant="secondary" size="sm" onClick={() => { setFilters(DEFAULT_FILTERS); setActiveCity(undefined) }}>
                Clear filters
              </Button>
            </div>
          ) : view === 'grid' ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {items.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  riskScore={project.risk_score ?? undefined}
                />
              ))}
            </div>
          ) : (
            <div className="space-y-2.5">
              {items.map((project) => (
                <ProjectListItem
                  key={project.id}
                  project={project}
                  riskScore={project.risk_score ?? undefined}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-8 pt-5 border-t border-slate-100">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Previous
              </Button>
              <span className="text-sm text-slate-500">Page {page + 1} of {totalPages}</span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile filter sheet */}
      {mobileFilters && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMobileFilters(false)} />
          <div className="relative mt-auto bg-white rounded-t-3xl p-4 pb-8 max-h-[85vh] overflow-y-auto animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-propiq-navy">Filters</h3>
              <button onClick={() => setMobileFilters(false)} className="text-sm text-propiq-blue font-medium">Done</button>
            </div>
            <FilterPanel filters={filters} onChange={setFilters} />
          </div>
        </div>
      )}
    </div>
  )
}
