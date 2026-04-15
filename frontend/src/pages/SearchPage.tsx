import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { SlidersHorizontal } from 'lucide-react'
import { useSearchProjects } from '@/hooks'
import {
  ProjectListItem, FilterPanel, ListItemSkeleton, Button,
} from '@/components'
import { DEFAULT_FILTERS, type FilterValues } from '@/components/search/FilterPanel'
import type { ProjectSearchParams, RiskBand } from '@/types'

type SortOption = 'score' | 'price' | 'possession_date'

const PAGE_SIZE = 20

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''

  const [filters, setFilters] = useState<FilterValues>(DEFAULT_FILTERS)
  const [sort, setSort] = useState<SortOption>('score')
  const [page, setPage] = useState(0)
  const [mobileFilters, setMobileFilters] = useState(false)

  useEffect(() => { document.title = q ? `"${q}" — PropIQ Search` : 'Search — PropIQ' }, [q])

  // Reset page when query or filters change
  useEffect(() => { setPage(0) }, [q, filters, sort])

  const params: ProjectSearchParams = {
    q: q || undefined,
    city: filters.cities.length === 1 ? filters.cities[0] : undefined,
    risk_band: filters.riskBands.length === 1 ? (filters.riskBands[0] as RiskBand) : undefined,
    project_type: filters.projectType || undefined,
    min_price: filters.minPricePSF > 2000 ? filters.minPricePSF : undefined,
    max_price: filters.maxPricePSF < 30000 ? filters.maxPricePSF : undefined,
    sort_by: sort,
    sort_dir: sort === 'price' ? 'asc' : 'desc',
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  }

  const { data, isLoading, isError, refetch } = useSearchProjects(params, true)

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Query header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-propiq-navy">
          {q ? (
            <>Search results for <span className="text-propiq-blue">"{q}"</span></>
          ) : (
            'Browse all projects'
          )}
        </h1>
        {!isLoading && (
          <p className="text-sm text-slate-500 mt-1">
            {total > 0
              ? `${total.toLocaleString('en-IN')} project${total !== 1 ? 's' : ''} found`
              : 'No projects found'}
          </p>
        )}
      </div>

      <div className="flex gap-6 items-start">
        {/* ── Filter sidebar (desktop) ── */}
        <aside className="hidden lg:block w-72 shrink-0">
          <FilterPanel filters={filters} onChange={setFilters} />
        </aside>

        {/* ── Main results ── */}
        <div className="flex-1 min-w-0">
          {/* Sort + mobile filter button */}
          <div className="flex items-center justify-between mb-4 gap-3">
            <button
              onClick={() => setMobileFilters(true)}
              className="lg:hidden flex items-center gap-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-xl px-3 py-2 hover:bg-slate-50"
            >
              <SlidersHorizontal size={14} /> Filters
              {Object.values(filters).some((v) => Array.isArray(v) ? v.length > 0 : !!v) && (
                <span className="w-4 h-4 bg-propiq-blue text-white rounded-full text-2xs font-bold flex items-center justify-center">!</span>
              )}
            </button>

            <div className="flex items-center gap-2 ml-auto">
              <span className="text-xs text-slate-500 hidden sm:block">Sort:</span>
              {([
                { value: 'score',           label: 'Most Safe' },
                { value: 'possession_date', label: 'Best Appreciation' },
                { value: 'price',           label: 'Lowest Price' },
              ] as { value: SortOption; label: string }[]).map(({ value, label }) => (
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
            </div>
          </div>

          {/* Results list */}
          {isError ? (
            <div className="text-center py-16">
              <p className="text-slate-500 mb-3">Something went wrong loading results.</p>
              <Button variant="secondary" size="sm" onClick={() => refetch()}>Retry</Button>
            </div>
          ) : isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => <ListItemSkeleton key={i} />)}
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-4xl mb-4">🔍</p>
              <h3 className="font-semibold text-propiq-navy mb-1">No projects found</h3>
              <p className="text-sm text-slate-500">Try a different search term or adjust your filters.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {items.map((project) => (
                <ProjectListItem
                  key={project.id}
                  project={project}
                  riskScore={project.risk_score}
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
              <span className="text-sm text-slate-500">
                Page {page + 1} of {totalPages}
              </span>
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
