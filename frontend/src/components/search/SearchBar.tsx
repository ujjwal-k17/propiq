import {
  useState,
  useRef,
  useEffect,
  type KeyboardEvent,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, X, Loader2, Building2, MapPin } from 'lucide-react'
import clsx from 'clsx'
import { useSearchSuggestions } from '@/hooks'
import type { SearchSuggestion } from '@/types'
import { getRiskColor } from '@/utils/formatters'

export interface SearchBarProps {
  onSearch?: (query: string) => void
  placeholder?: string
  autoFocus?: boolean
  className?: string
  size?: 'sm' | 'lg'
}

export function SearchBar({
  onSearch,
  placeholder = 'Search projects, developers, RERA numbers...',
  autoFocus = false,
  className,
  size = 'sm',
}: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const { data: suggestions = [], isFetching } = useSearchSuggestions(query)

  // Close dropdown on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false)
        setActiveIdx(-1)
      }
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const submit = (q = query) => {
    const trimmed = q.trim()
    if (!trimmed) return
    setOpen(false)
    setActiveIdx(-1)
    if (onSearch) {
      onSearch(trimmed)
    } else {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`)
    }
  }

  const selectSuggestion = (s: SearchSuggestion) => {
    setQuery(s.label)
    setOpen(false)
    setActiveIdx(-1)
    if (s.type === 'project') navigate(`/projects/${s.id}`)
    else if (s.type === 'developer') navigate(`/developers/${s.id}`)
    else navigate(`/search?q=${encodeURIComponent(s.label)}`)
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!open || suggestions.length === 0) {
      if (e.key === 'Enter') submit()
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIdx >= 0 && suggestions[activeIdx]) {
        selectSuggestion(suggestions[activeIdx])
      } else {
        submit()
      }
    } else if (e.key === 'Escape') {
      setOpen(false)
      setActiveIdx(-1)
    }
  }

  const isLg = size === 'lg'

  return (
    <div ref={containerRef} className={clsx('relative', className)}>
      <div
        className={clsx(
          'flex items-center gap-2 border rounded-xl bg-white transition-all duration-150',
          'focus-within:ring-2 focus-within:ring-propiq-blue/30 focus-within:border-propiq-blue',
          isLg ? 'px-4 py-3.5' : 'px-3 py-2',
          open && suggestions.length > 0 ? 'rounded-b-none border-b-transparent' : '',
        )}
      >
        {isFetching ? (
          <Loader2 size={isLg ? 20 : 16} className="shrink-0 text-propiq-blue animate-spin" />
        ) : (
          <Search size={isLg ? 20 : 16} className="shrink-0 text-slate-400" />
        )}

        <input
          ref={inputRef}
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
            setActiveIdx(-1)
          }}
          onFocus={() => query.length >= 2 && setOpen(true)}
          onKeyDown={handleKey}
          placeholder={placeholder}
          aria-label="Search PropIQ"
          aria-autocomplete="list"
          aria-controls="search-suggestions"
          aria-activedescendant={activeIdx >= 0 ? `suggestion-${activeIdx}` : undefined}
          className={clsx(
            'flex-1 bg-transparent outline-none text-slate-900 placeholder:text-slate-400',
            isLg ? 'text-base' : 'text-sm',
          )}
        />

        {query && (
          <button
            onClick={() => { setQuery(''); setOpen(false); inputRef.current?.focus() }}
            aria-label="Clear search"
            className="p-0.5 rounded text-slate-300 hover:text-slate-500 transition-colors"
          >
            <X size={14} />
          </button>
        )}

        {!query && (
          <button
            onClick={() => submit()}
            aria-label="Search"
            className={clsx(
              'shrink-0 bg-propiq-navy text-white rounded-lg font-medium transition-colors hover:bg-navy-600',
              isLg ? 'px-4 py-1.5 text-sm' : 'px-3 py-1 text-xs',
            )}
          >
            Search
          </button>
        )}
      </div>

      {/* Suggestions dropdown */}
      {open && suggestions.length > 0 && (
        <div
          id="search-suggestions"
          role="listbox"
          aria-label="Search suggestions"
          className="absolute top-full left-0 right-0 bg-white border border-t-0 border-propiq-blue rounded-b-xl shadow-card-hover overflow-hidden z-50 max-h-72 overflow-y-auto"
        >
          {/* Group by type */}
          {(['project', 'developer', 'city'] as const).map((type) => {
            const group = suggestions.filter((s) => s.type === type)
            if (group.length === 0) return null
            const label = type === 'project' ? 'Projects' : type === 'developer' ? 'Developers' : 'Cities'
            return (
              <div key={type}>
                <div className="px-4 py-1.5 bg-slate-50 border-b border-slate-100">
                  <span className="text-2xs font-semibold text-slate-400 uppercase tracking-wide">
                    {label}
                  </span>
                </div>
                {group.map((s) => {
                  const globalIdx = suggestions.indexOf(s)
                  return (
                    <SuggestionItem
                      key={s.id}
                      suggestion={s}
                      active={globalIdx === activeIdx}
                      id={`suggestion-${globalIdx}`}
                      onSelect={() => selectSuggestion(s)}
                      onHover={() => setActiveIdx(globalIdx)}
                    />
                  )
                })}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function SuggestionItem({
  suggestion,
  active,
  id,
  onSelect,
  onHover,
}: {
  suggestion: SearchSuggestion
  active: boolean
  id: string
  onSelect: () => void
  onHover: () => void
}) {
  const Icon = suggestion.type === 'developer' ? Building2 : MapPin

  return (
    <div
      id={id}
      role="option"
      aria-selected={active}
      onClick={onSelect}
      onMouseEnter={onHover}
      className={clsx(
        'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors',
        active ? 'bg-navy-50' : 'hover:bg-slate-50',
      )}
    >
      <Icon size={14} className="shrink-0 text-slate-400" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{suggestion.label}</p>
        {suggestion.sublabel && (
          <p className="text-xs text-slate-400 truncate">{suggestion.sublabel}</p>
        )}
      </div>
    </div>
  )
}
