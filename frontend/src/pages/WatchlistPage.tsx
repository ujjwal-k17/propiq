import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bookmark, Trash2 } from 'lucide-react'
import { getProjectDetail, removeFromWatchlist } from '@/services/api'
import { useAuthStore } from '@/store'
import { ProjectCard, ProjectCardSkeleton, Button } from '@/components'
import type { ProjectDetail } from '@/types'

export function WatchlistPage() {
  const { user, updateUser } = useAuthStore()
  const qc = useQueryClient()
  const watchlistIds = user?.watchlist_project_ids ?? []

  useEffect(() => { document.title = 'Watchlist — PropIQ' }, [])

  // Fetch all watchlisted project details in parallel using useQueries
  const results = useQueries({
    queries: watchlistIds.map((id) => ({
      queryKey: ['project-detail', id],
      queryFn: () => getProjectDetail(id),
      staleTime: 10 * 60 * 1000,
    })),
  })

  const removeMutation = useMutation({
    mutationFn: (projectId: string) => removeFromWatchlist(projectId),
    onSuccess: (_, projectId) => {
      if (user) {
        updateUser({
          ...user,
          watchlist_project_ids: user.watchlist_project_ids.filter((id) => id !== projectId),
        })
      }
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })

  const isLoading = results.some((r) => r.isLoading)
  const projectDetails = results
    .map((r) => r.data as ProjectDetail | undefined)
    .filter((d): d is ProjectDetail => !!d)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-propiq-navy">My Watchlist</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {watchlistIds.length === 0
              ? 'Save projects to track them here'
              : `${watchlistIds.length} saved project${watchlistIds.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        {watchlistIds.length > 0 && (
          <Link to="/discover">
            <Button variant="secondary" size="sm">Browse more projects</Button>
          </Link>
        )}
      </div>

      {watchlistIds.length === 0 ? (
        <div className="bg-surface rounded-3xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-propiq-navy/10 flex items-center justify-center mx-auto mb-4">
            <Bookmark size={28} className="text-propiq-navy/40" />
          </div>
          <h3 className="font-semibold text-propiq-navy mb-2">No saved projects yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
            Click the bookmark icon on any project card to save it here for easy access.
          </p>
          <Link to="/discover">
            <Button variant="primary" size="sm">Discover projects</Button>
          </Link>
        </div>
      ) : isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {watchlistIds.map((id) => <ProjectCardSkeleton key={id} />)}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {watchlistIds.map((id) => {
            const detail = projectDetails.find((d) => d.project.id === id)
            if (!detail) return <ProjectCardSkeleton key={id} />

            return (
              <div key={id} className="relative group">
                <ProjectCard
                  project={detail.project}
                  riskScore={detail.risk_score ?? undefined}
                />
                <button
                  onClick={() => removeMutation.mutate(id)}
                  disabled={removeMutation.isPending && removeMutation.variables === id}
                  className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-lg p-1.5 text-slate-400 hover:text-red-500 shadow-sm"
                  aria-label="Remove from watchlist"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
