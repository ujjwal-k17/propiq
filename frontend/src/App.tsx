import { type ReactNode, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'

import { useAuthStore, useUIStore } from '@/store'
import { useAlerts } from '@/hooks'
import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import { AuthModal } from '@/components/auth/AuthModal'
import { UpgradeModal } from '@/components/ui/UpgradeModal'

import { HomePage }            from '@/pages/HomePage'
import { SearchPage }          from '@/pages/SearchPage'
import { ProjectDetailPage }   from '@/pages/ProjectDetailPage'
import { DeveloperProfilePage } from '@/pages/DeveloperProfilePage'
import { ComparePage }         from '@/pages/ComparePage'
import { DiscoverPage }        from '@/pages/DiscoverPage'
import { WatchlistPage }       from '@/pages/WatchlistPage'
import { ChatPage }            from '@/pages/ChatPage'
import { PricingPage }         from '@/pages/PricingPage'
import { ProfilePage }         from '@/pages/ProfilePage'

// ── Scroll to top on navigation ───────────────────────────────────────────────

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }) }, [pathname])
  return null
}

// ── Protected route ───────────────────────────────────────────────────────────

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const { openAuthModal }   = useUIStore()

  useEffect(() => {
    if (!isAuthenticated) openAuthModal()
  }, [isAuthenticated, openAuthModal])

  if (!isAuthenticated) return <Navigate to="/" replace />
  return <>{children}</>
}

// ── Layout wrapper (Navbar + Footer) ─────────────────────────────────────────

function AppShell({ children }: { children: ReactNode }) {
  useAlerts()
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

export function App() {
  return (
    <>
      <ScrollToTop />

      <Routes>
        <Route
          path="/"
          element={
            <AppShell>
              <HomePage />
            </AppShell>
          }
        />
        <Route
          path="/search"
          element={
            <AppShell>
              <SearchPage />
            </AppShell>
          }
        />
        <Route
          path="/project/:id"
          element={
            <AppShell>
              <ProjectDetailPage />
            </AppShell>
          }
        />
        {/* Legacy route compat */}
        <Route path="/projects/:id" element={<Navigate to="/project/:id" replace />} />

        <Route
          path="/developer/:id"
          element={
            <AppShell>
              <DeveloperProfilePage />
            </AppShell>
          }
        />
        <Route
          path="/compare"
          element={
            <AppShell>
              <ComparePage />
            </AppShell>
          }
        />
        <Route
          path="/discover"
          element={
            <AppShell>
              <DiscoverPage />
            </AppShell>
          }
        />
        <Route
          path="/pricing"
          element={
            <AppShell>
              <PricingPage />
            </AppShell>
          }
        />
        <Route
          path="/watchlist"
          element={
            <AppShell>
              <ProtectedRoute>
                <WatchlistPage />
              </ProtectedRoute>
            </AppShell>
          }
        />
        <Route
          path="/chat"
          element={
            <AppShell>
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            </AppShell>
          }
        />
        <Route
          path="/profile"
          element={
            <AppShell>
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            </AppShell>
          }
        />

        {/* Redirect old /login route to home (auth is now modal-based) */}
        <Route path="/login"    element={<Navigate to="/" replace />} />
        <Route path="/register" element={<Navigate to="/" replace />} />

        {/* 404 */}
        <Route
          path="*"
          element={
            <AppShell>
              <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
                <p className="text-6xl font-bold text-propiq-navy/20 mb-4">404</p>
                <h1 className="text-2xl font-bold text-propiq-navy mb-2">Page not found</h1>
                <p className="text-slate-500 mb-6">The page you're looking for doesn't exist.</p>
                <a href="/" className="px-5 py-2.5 bg-propiq-navy text-white rounded-xl font-medium hover:bg-navy-600 transition-colors">
                  Go home
                </a>
              </div>
            </AppShell>
          }
        />
      </Routes>

      {/* Global modals rendered at root level */}
      <AuthModal />
      <UpgradeModal />
    </>
  )
}
