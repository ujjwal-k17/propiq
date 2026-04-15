import { type ReactNode } from 'react'
import { Lock, CheckCircle2 } from 'lucide-react'
import { useUIStore } from '@/store'
import { Button } from './Button'

const DEFAULT_FEATURES = [
  '6 risk dimensions with detailed breakdown',
  'All risk flags and critical alerts',
  'Price appreciation forecast (3yr / 5yr)',
  'Downloadable PDF report',
  'Unlimited AI chat for this project',
]

export interface UpgradeGateProps {
  isLocked: boolean
  feature?: string
  features?: string[]
  children: ReactNode
}

export function UpgradeGate({
  isLocked,
  feature = 'Full Diligence Report',
  features = DEFAULT_FEATURES,
  children,
}: UpgradeGateProps) {
  const { openUpgradeModal } = useUIStore()

  if (!isLocked) return <>{children}</>

  return (
    <div className="relative">
      {/* Blurred preview */}
      <div
        className="blur-sm pointer-events-none select-none overflow-hidden max-h-64"
        aria-hidden="true"
      >
        {children}
      </div>

      {/* Gate overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-b from-white/40 to-white/90">
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-6 max-w-sm w-full mx-4">
          <div className="text-center mb-5">
            <div className="w-12 h-12 rounded-full bg-navy-50 border-2 border-propiq-navy/20 flex items-center justify-center mx-auto mb-3">
              <Lock size={20} className="text-propiq-navy" />
            </div>
            <h3 className="font-bold text-propiq-navy text-lg">Unlock {feature}</h3>
            <p className="text-sm text-slate-500 mt-1">
              ₹499 per report&ensp;·&ensp;₹999/month Pro
            </p>
          </div>

          <ul className="space-y-2 mb-5">
            {features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                <CheckCircle2 size={14} className="text-propiq-teal mt-0.5 shrink-0" />
                {f}
              </li>
            ))}
          </ul>

          <Button variant="primary" size="md" className="w-full" onClick={openUpgradeModal}>
            Upgrade to Pro
          </Button>
          <p className="text-center text-xs text-slate-400 mt-2">Cancel anytime. No hidden fees.</p>
        </div>
      </div>
    </div>
  )
}
