import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { searchQuery, getSearchSuggestions } from '@/services/api'
import type { SearchResult, SearchSuggestion } from '@/types'

// ─── Debounce primitive ───────────────────────────────────────────────────────

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

// ─── useSearch ────────────────────────────────────────────────────────────────

/**
 * Debounced full-text search across projects + developers.
 * - Waits 300 ms after the user stops typing before firing.
 * - Returns loading state during debounce to avoid flicker.
 */
export function useSearch(query: string) {
  const debouncedQuery = useDebounced(query.trim(), 300)
  const isDebouncing = query.trim() !== debouncedQuery

  const result = useQuery<SearchResult>({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchQuery(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 60 * 1000,  // 1 min
    gcTime: 5 * 60 * 1000,
    placeholderData: (prev) => prev,
  })

  return {
    ...result,
    isLoading: result.isLoading || isDebouncing,
    debouncedQuery,
  }
}

// ─── useSearchSuggestions ─────────────────────────────────────────────────────

/**
 * Typeahead suggestions for the search bar.
 * Fires after 300 ms with a minimum 2-character query.
 * Returns at most 8 suggestions (enforced server-side).
 */
export function useSearchSuggestions(query: string) {
  const debouncedQuery = useDebounced(query.trim(), 300)

  return useQuery<SearchSuggestion[]>({
    queryKey: ['search', 'suggestions', debouncedQuery],
    queryFn: () => getSearchSuggestions(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30 * 1000,
    gcTime: 2 * 60 * 1000,
    placeholderData: (prev) => prev,
  })
}
