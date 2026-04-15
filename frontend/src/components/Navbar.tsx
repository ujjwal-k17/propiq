import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, Search, User, LogOut, Menu, X } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export function Navbar() {
  const [query, setQuery] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const { isAuthenticated, user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-indigo-600 font-bold text-xl shrink-0">
          <Shield size={20} />
          PropIQ
        </Link>

        {/* Search */}
        <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-md relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search projects, developers..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </form>

        <div className="flex-1" />

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-1">
          <Link to="/projects" className="px-3 py-2 text-sm text-slate-600 hover:text-indigo-600 font-medium rounded-lg hover:bg-slate-50">
            Projects
          </Link>
          <Link to="/developers" className="px-3 py-2 text-sm text-slate-600 hover:text-indigo-600 font-medium rounded-lg hover:bg-slate-50">
            Developers
          </Link>
          {isAuthenticated ? (
            <div className="flex items-center gap-2 ml-2">
              <span className="text-sm text-slate-500">{user?.full_name}</span>
              <button
                onClick={() => { logout(); navigate('/') }}
                className="p-2 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 ml-2">
              <Link to="/login" className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-indigo-600">
                Sign in
              </Link>
              <Link to="/register" className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
                Get Started
              </Link>
            </div>
          )}
        </div>

        {/* Mobile menu toggle */}
        <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden p-2 text-slate-500">
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-slate-100 px-4 py-4 space-y-2 bg-white">
          <form onSubmit={handleSearch} className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none"
            />
          </form>
          <Link to="/projects" onClick={() => setMenuOpen(false)} className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-lg">
            Projects
          </Link>
          <Link to="/developers" onClick={() => setMenuOpen(false)} className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-lg">
            Developers
          </Link>
          {!isAuthenticated && (
            <Link to="/login" onClick={() => setMenuOpen(false)} className="block px-3 py-2 text-sm font-semibold text-indigo-600">
              Sign In / Register
            </Link>
          )}
        </div>
      )}
    </nav>
  )
}
