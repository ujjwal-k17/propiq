import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Shield, Menu, X, ChevronDown, LogOut, User,
  BookMarked, BarChart3, Compass,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuthStore, useUIStore } from '@/store'
import { SearchBar } from '@/components/search/SearchBar'
import { Badge } from '@/components/ui/Badge'
import { AlertBell } from '@/components/alerts/AlertBell'
import { AlertPanel } from '@/components/alerts/AlertPanel'

const NAV_LINKS = [
  { to: '/discover', label: 'Discover', icon: Compass },
  { to: '/compare',  label: 'Compare',  icon: BarChart3 },
  { to: '/watchlist', label: 'Watchlist', icon: BookMarked },
]

export function Navbar() {
  const [menuOpen, setMenuOpen]             = useState(false)
  const [userMenuOpen, setUserMenuOpen]     = useState(false)
  const [alertPanelOpen, setAlertPanelOpen] = useState(false)
  const { isAuthenticated, user, logout } = useAuthStore()
  const { openAuthModal } = useUIStore()
  const navigate = useNavigate()
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close user dropdown on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (!userMenuRef.current?.contains(e.target as Node)) setUserMenuOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const isPro = user?.subscription_tier === 'pro' || user?.subscription_tier === 'enterprise'

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? 'U'

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-4">

        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-2 text-propiq-navy font-bold text-xl shrink-0 hover:text-propiq-blue transition-colors"
          aria-label="PropIQ home"
        >
          <div className="w-7 h-7 rounded-lg bg-propiq-gradient flex items-center justify-center">
            <Shield size={15} className="text-white" />
          </div>
          <span>PropIQ</span>
        </Link>

        {/* Search bar — desktop center */}
        <div className="hidden md:block flex-1 max-w-xl">
          <SearchBar size="sm" />
        </div>

        <div className="flex-1 md:hidden" />

        {/* Nav links — desktop */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:text-propiq-navy font-medium rounded-lg hover:bg-slate-50 transition-colors"
            >
              <Icon size={14} />
              {label}
            </Link>
          ))}
        </div>

        {/* Alert bell (authenticated users only) */}
        {isAuthenticated && (
          <div className="relative hidden md:block">
            <AlertBell
              open={alertPanelOpen}
              onToggle={() => setAlertPanelOpen((x) => !x)}
            />
            <AlertPanel
              open={alertPanelOpen}
              onClose={() => setAlertPanelOpen(false)}
            />
          </div>
        )}

        {/* Auth area */}
        {isAuthenticated && user ? (
          <div ref={userMenuRef} className="relative hidden md:block">
            <button
              onClick={() => setUserMenuOpen((x) => !x)}
              aria-expanded={userMenuOpen}
              aria-label="User menu"
              className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl hover:bg-slate-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy"
            >
              <div className="w-8 h-8 rounded-full bg-propiq-gradient flex items-center justify-center text-white font-bold text-xs font-mono">
                {initials}
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-propiq-navy leading-none">{user.full_name ?? user.email}</p>
                {isPro && (
                  <Badge label={user.subscription_tier === 'enterprise' ? 'Enterprise' : 'Pro'} color="teal" size="sm" />
                )}
              </div>
              <ChevronDown size={14} className={clsx('text-slate-400 transition-transform', userMenuOpen && 'rotate-180')} />
            </button>

            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-52 bg-white border border-slate-100 rounded-xl shadow-card-hover py-1 animate-fade-in">
                <Link
                  to="/profile"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  <User size={14} /> My Profile
                </Link>
                <Link
                  to="/watchlist"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  <BookMarked size={14} /> My Watchlist
                </Link>
                <div className="border-t border-slate-100 my-1" />
                <button
                  onClick={() => { logout(); navigate('/'); setUserMenuOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={14} /> Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-2">
            <button
              onClick={openAuthModal}
              className="px-4 py-2 text-sm font-medium text-propiq-navy hover:text-propiq-blue transition-colors"
            >
              Sign in
            </button>
            <button
              onClick={openAuthModal}
              className="px-4 py-2 text-sm font-semibold text-white bg-propiq-navy hover:bg-navy-600 rounded-lg transition-colors"
            >
              Get Started
            </button>
          </div>
        )}

        {/* Mobile menu toggle */}
        <button
          onClick={() => setMenuOpen((x) => !x)}
          className="md:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
          aria-expanded={menuOpen}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-slate-100 bg-white animate-fade-in">
          <div className="px-4 py-3">
            <SearchBar size="sm" />
          </div>
          <div className="px-2 pb-3 space-y-1">
            {NAV_LINKS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 rounded-lg font-medium"
              >
                <Icon size={15} /> {label}
              </Link>
            ))}
            <div className="border-t border-slate-100 pt-2 mt-2">
              {isAuthenticated ? (
                <button
                  onClick={() => { logout(); navigate('/'); setMenuOpen(false) }}
                  className="flex items-center gap-2 px-3 py-2.5 text-sm text-red-600 w-full hover:bg-red-50 rounded-lg"
                >
                  <LogOut size={15} /> Sign out
                </button>
              ) : (
                <button
                  onClick={() => { openAuthModal(); setMenuOpen(false) }}
                  className="w-full px-3 py-2.5 text-sm font-semibold text-white bg-propiq-navy rounded-lg"
                >
                  Sign in / Register
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
