import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { User, Bell, Shield, LogOut, CheckCircle2 } from 'lucide-react'
import { getMe, updateMe } from '@/services/api'
import { useAuthStore } from '@/store'
import { Button, Input } from '@/components'
import type { RiskAppetite, SubscriptionTier } from '@/types'

const CITIES = ['Mumbai', 'Bengaluru', 'Pune', 'Hyderabad', 'Delhi NCR', 'Chennai', 'Ahmedabad', 'Kolkata']

const RISK_APPETITE_OPTIONS: { value: RiskAppetite; label: string; desc: string }[] = [
  { value: 'conservative', label: 'Conservative', desc: 'Focus on low-risk projects with stable returns' },
  { value: 'moderate', label: 'Moderate', desc: 'Balance between risk and return potential' },
  { value: 'aggressive', label: 'Aggressive', desc: 'Higher risk tolerance for better appreciation' },
]

const TIER_LABELS: Record<SubscriptionTier, string> = {
  free: 'Free',
  basic: 'Basic',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

const TIER_COLORS: Record<SubscriptionTier, string> = {
  free: 'text-slate-500 bg-slate-100',
  basic: 'text-propiq-blue bg-blue-50',
  pro: 'text-propiq-teal bg-teal-50',
  enterprise: 'text-amber-700 bg-amber-50',
}

export function ProfilePage() {
  const { user, updateUser, logout } = useAuthStore()
  const [saved, setSaved] = useState(false)

  useEffect(() => { document.title = 'Profile — PropIQ' }, [])

  // Sync fresh user from backend
  const { data: freshUser } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,
  })

  // Form state
  const [form, setForm] = useState({
    full_name: user?.full_name ?? '',
    phone: user?.phone ?? '',
    preferred_cities: user?.preferred_cities ?? [],
    risk_appetite: (user?.risk_appetite ?? 'moderate') as RiskAppetite,
  })

  // Keep form in sync when fresh data arrives
  useEffect(() => {
    if (freshUser) {
      setForm({
        full_name: freshUser.full_name ?? '',
        phone: freshUser.phone ?? '',
        preferred_cities: freshUser.preferred_cities ?? [],
        risk_appetite: freshUser.risk_appetite ?? 'moderate',
      })
    }
  }, [freshUser])

  const mutation = useMutation({
    mutationFn: () => updateMe(form),
    onSuccess: (updatedUser) => {
      updateUser(updatedUser)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const toggleCity = (city: string) => {
    setForm((prev) => ({
      ...prev,
      preferred_cities: prev.preferred_cities.includes(city)
        ? prev.preferred_cities.filter((c) => c !== city)
        : [...prev.preferred_cities, city],
    }))
  }

  const tier = (freshUser ?? user)?.subscription_tier ?? 'free'
  const email = (freshUser ?? user)?.email ?? ''

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold text-propiq-navy mb-6">My Profile</h1>

      {/* Account overview */}
      <div className="bg-white rounded-2xl shadow-card p-5 mb-5">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-14 h-14 rounded-2xl bg-propiq-gradient flex items-center justify-center text-white text-xl font-bold">
            {(form.full_name || email).charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-bold text-propiq-navy">{form.full_name || 'Your Name'}</p>
            <p className="text-sm text-slate-500">{email}</p>
            <span className={`inline-block mt-1 text-xs font-bold rounded-full px-2.5 py-0.5 ${TIER_COLORS[tier]}`}>
              {TIER_LABELS[tier]} Plan
            </span>
          </div>
        </div>

        {tier === 'free' && (
          <div className="bg-propiq-gradient rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-bold text-white text-sm">Upgrade to Pro</p>
              <p className="text-white/70 text-xs mt-0.5">Unlock full risk reports, AI assistant & more</p>
            </div>
            <Button
              variant="primary"
              size="sm"
              className="bg-white !text-propiq-navy hover:bg-navy-50"
            >
              Upgrade
            </Button>
          </div>
        )}
      </div>

      {/* Profile form */}
      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
        className="space-y-5"
      >
        <div className="bg-white rounded-2xl shadow-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <User size={15} className="text-propiq-navy" />
            <h2 className="font-semibold text-propiq-navy text-sm">Personal Information</h2>
          </div>

          <div className="space-y-4">
            <Input
              label="Full Name"
              value={form.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              placeholder="Your full name"
            />
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                disabled
                className="w-full text-sm border border-slate-200 rounded-xl px-3 py-2.5 bg-slate-50 text-slate-400 cursor-not-allowed"
              />
              <p className="text-xs text-slate-400 mt-1">Email cannot be changed</p>
            </div>
            <Input
              label="Phone (optional)"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              placeholder="+91 98765 43210"
              type="tel"
            />
          </div>
        </div>

        {/* Investment preferences */}
        <div className="bg-white rounded-2xl shadow-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={15} className="text-propiq-navy" />
            <h2 className="font-semibold text-propiq-navy text-sm">Investment Preferences</h2>
          </div>

          <div className="mb-5">
            <p className="text-xs font-medium text-slate-600 mb-2.5">Preferred Cities</p>
            <div className="flex flex-wrap gap-2">
              {CITIES.map((city) => (
                <button
                  key={city}
                  type="button"
                  onClick={() => toggleCity(city)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                    form.preferred_cities.includes(city)
                      ? 'bg-propiq-navy text-white border-propiq-navy'
                      : 'border-slate-200 text-slate-600 hover:border-propiq-blue'
                  }`}
                >
                  {city}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-slate-600 mb-2.5">Risk Appetite</p>
            <div className="space-y-2">
              {RISK_APPETITE_OPTIONS.map(({ value, label, desc }) => (
                <label
                  key={value}
                  className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                    form.risk_appetite === value
                      ? 'border-propiq-navy bg-propiq-navy/5'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="risk_appetite"
                    value={value}
                    checked={form.risk_appetite === value}
                    onChange={() => setForm((f) => ({ ...f, risk_appetite: value }))}
                    className="mt-0.5 accent-propiq-navy"
                  />
                  <div>
                    <p className="font-semibold text-sm text-propiq-navy">{label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Save button */}
        <div className="flex items-center justify-between">
          <Button
            type="submit"
            variant="primary"
            isLoading={mutation.isPending}
            leftIcon={saved ? <CheckCircle2 size={15} /> : undefined}
          >
            {saved ? 'Saved!' : 'Save changes'}
          </Button>

          {mutation.isError && (
            <p className="text-sm text-risk-high">Failed to save. Please try again.</p>
          )}
        </div>
      </form>

      {/* Security section */}
      <div className="bg-white rounded-2xl shadow-card p-5 mt-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={15} className="text-propiq-navy" />
          <h2 className="font-semibold text-propiq-navy text-sm">Security</h2>
        </div>
        <p className="text-sm text-slate-500 mb-4">
          Password changes and two-factor authentication management coming soon.
        </p>
      </div>

      {/* Sign out */}
      <div className="mt-6 pt-6 border-t border-slate-100">
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<LogOut size={14} />}
          onClick={logout}
          className="text-slate-500 hover:text-red-500"
        >
          Sign out
        </Button>
      </div>
    </div>
  )
}
