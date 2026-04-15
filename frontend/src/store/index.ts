/**
 * Zustand stores — canonical barrel export
 * ========================================
 * Import from here, not from individual store files:
 *
 *   import { useAuthStore, useUIStore, useAlertsStore } from '@/store'
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { ProjectAlert, User } from '@/types'

// ─── Auth store ───────────────────────────────────────────────────────────────

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  /** Set auth state after login / register */
  login: (token: string, user: User) => void
  /** Clear all auth state */
  logout: () => void
  /** Update user profile in place (after PUT /auth/me) */
  updateUser: (user: User) => void
  // legacy alias used in existing components
  setAuth: (user: User, token: string) => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (token, user) => set({ token, user, isAuthenticated: true }),

      logout: () => set({ token: null, user: null, isAuthenticated: false }),

      updateUser: (user) => set({ user }),

      // legacy aliases
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'propiq-auth',
      partialize: (s) => ({ token: s.token, user: s.user }),
    },
  ),
)

// ─── UI store ─────────────────────────────────────────────────────────────────

interface UIState {
  searchQuery: string
  selectedCity: string | null
  showAuthModal: boolean
  showUpgradeModal: boolean

  setSearchQuery: (q: string) => void
  setSelectedCity: (city: string | null) => void
  openAuthModal: () => void
  closeAuthModal: () => void
  openUpgradeModal: () => void
  closeUpgradeModal: () => void
}

export const useUIStore = create<UIState>()((set) => ({
  searchQuery: '',
  selectedCity: null,
  showAuthModal: false,
  showUpgradeModal: false,

  setSearchQuery: (q) => set({ searchQuery: q }),
  setSelectedCity: (city) => set({ selectedCity: city }),
  openAuthModal: () => set({ showAuthModal: true }),
  closeAuthModal: () => set({ showAuthModal: false }),
  openUpgradeModal: () => set({ showUpgradeModal: true }),
  closeUpgradeModal: () => set({ showUpgradeModal: false }),
}))

// ─── Alerts store ─────────────────────────────────────────────────────────────

interface AlertsState {
  /** All alerts received in this session (newest first). */
  alerts: ProjectAlert[]
  /** IDs that have been dismissed / read. */
  readIds: Set<string>
  /** WebSocket connection status. */
  wsStatus: 'disconnected' | 'connecting' | 'connected' | 'error'

  addAlert: (alert: ProjectAlert) => void
  setHistory: (alerts: ProjectAlert[]) => void
  markRead: (ids: string[]) => void
  markAllRead: () => void
  setWsStatus: (status: AlertsState['wsStatus']) => void

  /** Derived: count of alerts not in readIds. */
  unreadCount: () => number
}

export const useAlertsStore = create<AlertsState>()((set, get) => ({
  alerts: [],
  readIds: new Set(),
  wsStatus: 'disconnected',

  addAlert: (alert) =>
    set((s) => ({
      alerts: [alert, ...s.alerts].slice(0, 100),   // keep at most 100 in memory
    })),

  setHistory: (incoming) =>
    set((s) => {
      const existing = new Set(s.alerts.map((a) => a.id))
      const merged = [
        ...s.alerts,
        ...incoming.filter((a) => !existing.has(a.id)),
      ].sort((a, b) => (a.created_at > b.created_at ? -1 : 1)).slice(0, 100)
      // Seed readIds from server-side is_read field
      const newReadIds = new Set(s.readIds)
      incoming.forEach((a) => { if (a.is_read) newReadIds.add(a.id) })
      return { alerts: merged, readIds: newReadIds }
    }),

  markRead: (ids) =>
    set((s) => {
      const next = new Set(s.readIds)
      ids.forEach((id) => next.add(id))
      return { readIds: next }
    }),

  markAllRead: () =>
    set((s) => ({ readIds: new Set(s.alerts.map((a) => a.id)) })),

  setWsStatus: (wsStatus) => set({ wsStatus }),

  unreadCount: () => {
    const { alerts, readIds } = get()
    return alerts.filter((a) => !readIds.has(a.id)).length
  },
}))
