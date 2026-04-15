import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bot, ChevronDown } from 'lucide-react'
import { getProjectDetail } from '@/services/api'
import { ChatInterface } from '@/components'
import type { ProjectDetail } from '@/types'

export function ChatPage() {
  const [searchParams] = useSearchParams()
  const projectIdParam = searchParams.get('project')
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(
    projectIdParam ?? undefined,
  )
  const [showProjectPicker, setShowProjectPicker] = useState(false)

  useEffect(() => { document.title = 'AI Assistant — PropIQ' }, [])

  const { data: projectDetail } = useQuery<ProjectDetail>({
    queryKey: ['project-detail', selectedProjectId],
    queryFn: () => getProjectDetail(selectedProjectId!),
    enabled: !!selectedProjectId,
    staleTime: 10 * 60 * 1000,
  })

  const contextProject = projectDetail?.project ?? null

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 h-[calc(100vh-64px)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-propiq-gradient flex items-center justify-center">
            <Bot size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-propiq-navy">PropIQ AI Assistant</h1>
            <p className="text-xs text-slate-500">
              Ask about RERA compliance, developer risk, investment potential, and more
            </p>
          </div>
        </div>

        {/* Project context selector */}
        <div className="relative">
          <button
            onClick={() => setShowProjectPicker((v) => !v)}
            className="flex items-center gap-2 text-sm border border-slate-200 rounded-xl px-3 py-2 hover:bg-slate-50 transition-colors"
          >
            <span className="text-slate-600 truncate max-w-[160px]">
              {contextProject ? contextProject.name : 'No project context'}
            </span>
            <ChevronDown size={13} className="text-slate-400 shrink-0" />
          </button>

          {showProjectPicker && (
            <div className="absolute right-0 top-full mt-1 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-20 p-3">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 px-1">
                Set project context
              </p>
              <p className="text-xs text-slate-400 px-1 mb-3">
                Paste a project ID to focus the AI on that specific project.
              </p>
              <input
                type="text"
                placeholder="Enter project ID…"
                defaultValue={selectedProjectId ?? ''}
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-propiq-blue/30 focus:border-propiq-blue"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const val = (e.target as HTMLInputElement).value.trim()
                    setSelectedProjectId(val || undefined)
                    setShowProjectPicker(false)
                  }
                }}
              />
              <button
                onClick={() => {
                  setSelectedProjectId(undefined)
                  setShowProjectPicker(false)
                }}
                className="mt-2 w-full text-xs text-slate-500 hover:text-red-500 py-1 transition-colors"
              >
                Clear context
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Context pill */}
      {contextProject && (
        <div className="mb-3 shrink-0">
          <div className="inline-flex items-center gap-2 bg-propiq-navy/8 border border-propiq-navy/15 rounded-full px-3 py-1.5 text-xs text-propiq-navy">
            <span className="w-2 h-2 rounded-full bg-propiq-teal" />
            Discussing: <span className="font-semibold">{contextProject.name}</span>
            <span className="text-slate-400">·</span>
            <span className="text-slate-500">{contextProject.city}</span>
          </div>
        </div>
      )}

      {/* Chat interface — fills remaining height */}
      <div className="flex-1 min-h-0 bg-white rounded-2xl shadow-card overflow-hidden">
        <ChatInterface
          projectId={selectedProjectId}
          projectName={contextProject?.name}
        />
      </div>

      {/* Disclaimer */}
      <p className="text-center text-xs text-slate-400 mt-3 shrink-0">
        AI responses are for informational purposes only and do not constitute financial or legal advice.
        Always consult a SEBI-registered advisor before making investment decisions.
      </p>
    </div>
  )
}
