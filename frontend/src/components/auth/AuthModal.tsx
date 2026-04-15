import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Chrome } from 'lucide-react'
import clsx from 'clsx'
import { login, register, type LoginResponse, type RegisterPayload } from '@/services/api'
import { useAuthStore, useUIStore } from '@/store'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

type Tab = 'login' | 'register'

const CITIES = ['Mumbai', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Noida', 'Gurugram']

export function AuthModal() {
  const { showAuthModal, closeAuthModal } = useUIStore()
  const { login: storeLogin } = useAuthStore()

  const [tab, setTab] = useState<Tab>('login')
  const [apiError, setApiError] = useState<string | null>(null)

  // Login form state
  const [loginEmail, setLoginEmail]     = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Register form state
  const [regEmail,    setRegEmail]    = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regName,     setRegName]     = useState('')
  const [isNRI,       setIsNRI]       = useState(false)
  const [cities,      setCities]      = useState<string[]>([])

  const onSuccess = (data: LoginResponse) => {
    storeLogin(data.access_token, data.user ?? { id: '', email: loginEmail || regEmail, full_name: regName || null, subscription_tier: 'free', preferred_cities: cities, watchlist_project_ids: [], risk_appetite: 'moderate' })
    closeAuthModal()
    setApiError(null)
  }

  const loginMutation = useMutation<LoginResponse, Error, void>({
    mutationFn: () => login(loginEmail, loginPassword),
    onSuccess,
    onError: (e) => setApiError(e.message || 'Login failed. Please check your credentials.'),
  })

  const registerMutation = useMutation<LoginResponse, Error, void>({
    mutationFn: () => register({
      email: regEmail,
      password: regPassword,
      full_name: regName,
      preferred_cities: cities,
      is_nri: isNRI,
    } as RegisterPayload),
    onSuccess: (data) => {
      onSuccess(data)
    },
    onError: (e) => setApiError(e.message || 'Registration failed. Email may already be in use.'),
  })

  const toggleCity = (c: string) =>
    setCities((prev) => prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c])

  const handleTabChange = (t: Tab) => { setTab(t); setApiError(null) }

  return (
    <Modal
      isOpen={showAuthModal}
      onClose={closeAuthModal}
      size="sm"
      hideHeader
    >
      {/* Tab strip */}
      <div className="flex mb-6 border-b border-slate-100 -mx-5 px-5">
        {(['login', 'register'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => handleTabChange(t)}
            className={clsx(
              'flex-1 pb-3 text-sm font-semibold capitalize transition-colors',
              tab === t
                ? 'text-propiq-navy border-b-2 border-propiq-navy -mb-px'
                : 'text-slate-400 hover:text-slate-600',
            )}
          >
            {t === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        ))}
      </div>

      {/* Error */}
      {apiError && (
        <div className="mb-4 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5" role="alert">
          {apiError}
        </div>
      )}

      {tab === 'login' ? (
        <form
          onSubmit={(e) => { e.preventDefault(); setApiError(null); loginMutation.mutate() }}
          className="space-y-4"
        >
          <Input
            label="Email address"
            type="email"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <Input
            label="Password"
            type="password"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <div className="flex justify-end">
            <button type="button" className="text-xs text-propiq-blue hover:underline">
              Forgot password?
            </button>
          </div>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loginMutation.isPending}
            className="w-full"
          >
            Sign In
          </Button>

          <Divider />
          <SocialPlaceholder />

          <p className="text-center text-xs text-slate-500 mt-4">
            Don't have an account?{' '}
            <button type="button" onClick={() => handleTabChange('register')} className="text-propiq-blue font-medium hover:underline">
              Create one free
            </button>
          </p>
        </form>
      ) : (
        <form
          onSubmit={(e) => { e.preventDefault(); setApiError(null); registerMutation.mutate() }}
          className="space-y-4"
        >
          <Input
            label="Full name"
            value={regName}
            onChange={(e) => setRegName(e.target.value)}
            autoComplete="name"
          />
          <Input
            label="Email address"
            type="email"
            value={regEmail}
            onChange={(e) => setRegEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <Input
            label="Password"
            type="password"
            value={regPassword}
            onChange={(e) => setRegPassword(e.target.value)}
            autoComplete="new-password"
            hint="Minimum 8 characters"
            required
          />

          {/* NRI checkbox */}
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={isNRI}
              onChange={(e) => setIsNRI(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-propiq-blue focus:ring-propiq-blue"
            />
            <span className="text-sm text-slate-700">I am an NRI / overseas investor</span>
          </label>

          {/* City preferences */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Cities of interest (optional)</p>
            <div className="flex flex-wrap gap-1.5">
              {CITIES.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => toggleCity(c)}
                  className={clsx(
                    'px-2.5 py-1 text-xs rounded-full border font-medium transition-all',
                    cities.includes(c)
                      ? 'bg-propiq-navy text-white border-propiq-navy'
                      : 'border-slate-200 text-slate-600 hover:border-propiq-blue',
                  )}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={registerMutation.isPending}
            className="w-full"
          >
            Create Account
          </Button>

          <Divider />
          <SocialPlaceholder />

          <p className="text-center text-xs text-slate-500">
            Already have an account?{' '}
            <button type="button" onClick={() => handleTabChange('login')} className="text-propiq-blue font-medium hover:underline">
              Sign in
            </button>
          </p>
        </form>
      )}
    </Modal>
  )
}

function Divider() {
  return (
    <div className="flex items-center gap-2 my-1">
      <div className="flex-1 h-px bg-slate-100" />
      <span className="text-xs text-slate-400">or</span>
      <div className="flex-1 h-px bg-slate-100" />
    </div>
  )
}

function SocialPlaceholder() {
  return (
    <button
      type="button"
      disabled
      className="w-full flex items-center justify-center gap-2 border border-slate-200 rounded-lg py-2.5 text-sm text-slate-400 cursor-not-allowed"
      title="Coming soon"
    >
      <Chrome size={16} />
      Continue with Google
    </button>
  )
}
