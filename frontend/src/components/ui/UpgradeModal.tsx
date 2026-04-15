import { Check, Zap } from 'lucide-react'
import { useUIStore } from '@/store'
import { Modal } from './Modal'
import { Button } from './Button'

const FEATURES_FREE = [
  'Up to 5 project searches / day',
  'Overview tab only',
  'Basic risk band (Low / High)',
]

const FEATURES_PRO = [
  'Unlimited searches',
  'Full 6-dimension risk breakdown',
  'Price appreciation forecasts',
  'PDF diligence reports',
  'Unlimited AI chat',
  'Priority data refresh',
  'Developer financial analysis',
]

export function UpgradeModal() {
  const { showUpgradeModal, closeUpgradeModal } = useUIStore()
  return (
    <Modal isOpen={showUpgradeModal} onClose={closeUpgradeModal} title="Upgrade to PropIQ Pro" size="md">
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Free */}
        <div className="border border-slate-200 rounded-xl p-4">
          <p className="font-bold text-slate-700 mb-1">Free</p>
          <p className="text-2xl font-bold text-slate-900 mb-3">₹0</p>
          <ul className="space-y-1.5">
            {FEATURES_FREE.map((f) => (
              <li key={f} className="flex items-start gap-2 text-xs text-slate-600">
                <Check size={12} className="text-slate-400 mt-0.5 shrink-0" />{f}
              </li>
            ))}
          </ul>
        </div>

        {/* Pro */}
        <div className="border-2 border-propiq-teal rounded-xl p-4 bg-teal-50 relative">
          <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-propiq-teal text-white text-2xs font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wide">
            Recommended
          </span>
          <p className="font-bold text-propiq-teal mb-1 flex items-center gap-1">
            <Zap size={13} /> Pro
          </p>
          <p className="text-2xl font-bold text-propiq-navy mb-3">
            ₹999<span className="text-sm font-normal text-slate-500">/mo</span>
          </p>
          <ul className="space-y-1.5">
            {FEATURES_PRO.map((f) => (
              <li key={f} className="flex items-start gap-2 text-xs text-propiq-navy">
                <Check size={12} className="text-propiq-teal mt-0.5 shrink-0" />{f}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <Button variant="primary" size="lg" className="w-full mb-2">
        Start 7-day Free Trial → Pro
      </Button>
      <p className="text-center text-xs text-slate-400">
        No credit card required for trial. Cancel anytime.
      </p>
    </Modal>
  )
}
