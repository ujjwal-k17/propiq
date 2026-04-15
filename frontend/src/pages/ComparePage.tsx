import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, X, Share2, Check } from 'lucide-react'
import { useCompareProjects } from '@/hooks'
import { CompareTable, Button } from '@/components'

const MAX_PROJECTS = 3

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [copied, setCopied] = useState(false)

  // Project IDs from URL: ?ids=abc,def,ghi
  const idsParam = searchParams.get('ids') ?? ''
  const initialIds = idsParam ? idsParam.split(',').filter(Boolean).slice(0, MAX_PROJECTS) : []
  const [projectIds, setProjectIds] = useState<string[]>(initialIds)

  useEffect(() => { document.title = 'Compare Projects — PropIQ' }, [])

  // Keep URL in sync
  useEffect(() => {
    if (projectIds.length > 0) {
      setSearchParams({ ids: projectIds.join(',') }, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }, [projectIds, setSearchParams])

  const { data: comparison, isLoading, isError } = useCompareProjects(
    projectIds.length >= 2 ? projectIds : [],
  )

  const removeProject = (id: string) => {
    setProjectIds((prev) => prev.filter((pid) => pid !== id))
  }

  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback: select text
    }
  }, [])

  // SearchBar's onSelect gives us a project id from suggestion
  const [addInput, setAddInput] = useState('')

  const handleAddProject = () => {
    const id = addInput.trim()
    if (!id || projectIds.includes(id) || projectIds.length >= MAX_PROJECTS) return
    setProjectIds((prev) => [...prev, id])
    setAddInput('')
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-propiq-navy">Compare Projects</h1>
          <p className="text-sm text-slate-500 mt-0.5">Add up to {MAX_PROJECTS} projects to compare side-by-side</p>
        </div>
        {projectIds.length >= 2 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleShare}
            leftIcon={copied ? <Check size={14} /> : <Share2 size={14} />}
          >
            {copied ? 'Copied!' : 'Share'}
          </Button>
        )}
      </div>

      {/* Project selector chips + add button */}
      <div className="bg-white rounded-2xl shadow-card p-5 mb-6">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Selected projects ({projectIds.length}/{MAX_PROJECTS})
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          {projectIds.map((pid) => (
            <span
              key={pid}
              className="flex items-center gap-1.5 bg-propiq-navy/10 text-propiq-navy text-sm font-medium rounded-full px-3 py-1.5"
            >
              <span className="font-mono text-xs opacity-70">{pid.slice(0, 8)}…</span>
              <button
                onClick={() => removeProject(pid)}
                className="ml-1 hover:text-red-500 transition-colors"
                aria-label="Remove project"
              >
                <X size={13} />
              </button>
            </span>
          ))}

          {projectIds.length === 0 && (
            <p className="text-sm text-slate-400 italic">No projects selected yet</p>
          )}
        </div>

        {projectIds.length < MAX_PROJECTS && (
          <div className="border-t border-slate-100 pt-4">
            <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
              <Plus size={12} /> Add a project by ID
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddProject()}
                placeholder="Paste project ID…"
                className="flex-1 text-sm border border-slate-200 rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-propiq-blue/30 focus:border-propiq-blue"
              />
              <Button variant="primary" size="sm" onClick={handleAddProject} disabled={!addInput.trim()}>
                Add
              </Button>
            </div>
            <p className="text-xs text-slate-400 mt-1.5">
              Find project IDs on any project detail page (in the URL: /project/&#123;id&#125;)
            </p>
          </div>
        )}
      </div>

      {/* Comparison table */}
      {projectIds.length < 2 ? (
        <div className="bg-surface rounded-3xl p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-propiq-navy/10 flex items-center justify-center mx-auto mb-4">
            <Plus size={28} className="text-propiq-navy/50" />
          </div>
          <h3 className="font-semibold text-propiq-navy mb-2">Add at least 2 projects to compare</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Search for projects above and add them to see a side-by-side comparison of risk scores,
            pricing, developer track record, and appreciation potential.
          </p>
        </div>
      ) : isLoading ? (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : isError || !comparison ? (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center">
          <p className="text-slate-600 mb-3">Failed to load comparison. Make sure all project IDs are valid.</p>
          <Button variant="secondary" size="sm" onClick={() => setProjectIds([])}>
            Clear and start over
          </Button>
        </div>
      ) : (
        <CompareTable projects={comparison.projects} />
      )}
    </div>
  )
}
