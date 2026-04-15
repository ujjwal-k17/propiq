import { useCallback, useEffect, useRef, useState } from 'react'
import { CheckCircle2, X, Zap, Loader2, CheckCircle } from 'lucide-react'
import { useAuthStore, useUIStore } from '@/store'
import { createPaymentOrder, verifyPayment } from '@/services/api'
import type { BillingCycle, PlanId } from '@/types'

// ── Razorpay global type declaration ─────────────────────────────────────────

interface RazorpayOptions {
  key: string
  amount: number
  currency: string
  name: string
  description: string
  order_id: string
  prefill: { name: string; email: string }
  theme: { color: string }
  modal?: { ondismiss?: () => void }
  handler: (response: {
    razorpay_order_id: string
    razorpay_payment_id: string
    razorpay_signature: string
  }) => void
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => { open(): void }
  }
}

// ── Plan definitions ──────────────────────────────────────────────────────────

const PLANS = [
  {
    id: 'free' as const,
    name: 'Free',
    monthlyPrice: 0,
    annualPrice: 0,
    badge: null,
    description: 'For occasional research',
    cta: 'Get started free',
    ctaVariant: 'secondary' as const,
    features: [
      { text: '5 project searches per day', included: true },
      { text: 'Risk band (Low/Medium/High/Critical)', included: true },
      { text: 'Basic project details', included: true },
      { text: 'Full risk score breakdown', included: false },
      { text: 'Appreciation forecasts (3yr/5yr)', included: false },
      { text: 'PDF diligence report', included: false },
      { text: 'AI assistant', included: false },
      { text: 'Developer financial stress report', included: false },
      { text: 'Watchlist', included: false },
      { text: 'Unlimited searches', included: false },
    ],
  },
  {
    id: 'basic' as PlanId,
    name: 'Basic',
    monthlyPrice: 499,
    annualPrice: 399,
    badge: null,
    description: 'For active home buyers',
    cta: 'Start Basic',
    ctaVariant: 'secondary' as const,
    features: [
      { text: '50 project searches per day', included: true },
      { text: 'Risk band (Low/Medium/High/Critical)', included: true },
      { text: 'Basic project details', included: true },
      { text: 'Full risk score breakdown', included: true },
      { text: 'Appreciation forecasts (3yr/5yr)', included: true },
      { text: '3 PDF reports per month', included: true },
      { text: 'AI assistant', included: false },
      { text: 'Developer financial stress report', included: false },
      { text: 'Watchlist (up to 10)', included: true },
      { text: 'Unlimited searches', included: false },
    ],
  },
  {
    id: 'pro' as PlanId,
    name: 'Pro',
    monthlyPrice: 999,
    annualPrice: 799,
    badge: 'Most Popular',
    description: 'For serious investors & NRIs',
    cta: 'Start 7-day Free Trial',
    ctaVariant: 'primary' as const,
    features: [
      { text: 'Unlimited project searches', included: true },
      { text: 'Risk band (Low/Medium/High/Critical)', included: true },
      { text: 'Basic project details', included: true },
      { text: 'Full risk score breakdown', included: true },
      { text: 'Appreciation forecasts (3yr/5yr)', included: true },
      { text: 'Unlimited PDF reports', included: true },
      { text: 'AI assistant (unlimited)', included: true },
      { text: 'Developer financial stress report', included: true },
      { text: 'Unlimited watchlist', included: true },
      { text: 'Priority data refresh', included: true },
    ],
  },
]

const FAQ = [
  {
    q: 'Is the free plan really free?',
    a: 'Yes. The free plan has no credit card requirement and gives you 5 searches per day with risk band indicators. You only upgrade if you need the detailed breakdown, reports, or AI assistant.',
  },
  {
    q: 'What does the 7-day free trial include?',
    a: 'The free trial gives you full Pro access — unlimited searches, full risk score breakdown, appreciation forecasts, PDF reports, and AI assistant — for 7 days with no charges.',
  },
  {
    q: 'How is PropIQ data different from RERA portals?',
    a: 'RERA portals show raw registration data. PropIQ aggregates RERA, MCA21, court records, news, and transaction data into a single AI-powered risk score with actionable flags — saving you days of manual research.',
  },
  {
    q: 'Can I cancel any time?',
    a: "Yes. Cancel anytime from your profile. You'll retain Pro access until the end of your billing period.",
  },
]

// ── Razorpay script loader ────────────────────────────────────────────────────

function useRazorpayScript(): boolean {
  const [loaded, setLoaded] = useState(typeof window !== 'undefined' && !!window.Razorpay)

  useEffect(() => {
    if (loaded) return
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.onload = () => setLoaded(true)
    document.head.appendChild(script)
    return () => {
      // leave script in DOM for reuse across navigations
    }
  }, [loaded])

  return loaded
}

// ── Checkout hook ─────────────────────────────────────────────────────────────

function useRazorpayCheckout(annual: boolean) {
  const { isAuthenticated, updateUser } = useAuthStore()
  const { openAuthModal } = useUIStore()
  const scriptReady = useRazorpayScript()

  const [loading, setLoading] = useState<PlanId | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successPlan, setSuccessPlan] = useState<PlanId | null>(null)
  const rzpRef = useRef<{ open(): void } | null>(null)

  const checkout = useCallback(
    async (planId: PlanId) => {
      if (!isAuthenticated) { openAuthModal(); return }
      if (!scriptReady) { setError('Payment SDK not loaded. Please refresh.'); return }

      setError(null)
      setLoading(planId)

      try {
        const billingCycle: BillingCycle = annual ? 'annual' : 'monthly'
        const order = await createPaymentOrder(planId, billingCycle)

        const options: RazorpayOptions = {
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: 'PropIQ',
          description: `${planId.charAt(0).toUpperCase() + planId.slice(1)} Plan — ${billingCycle}`,
          order_id: order.order_id,
          prefill: { name: order.prefill_name, email: order.prefill_email },
          theme: { color: '#0F2D6B' },
          modal: {
            ondismiss: () => setLoading(null),
          },
          handler: async (response) => {
            try {
              const updatedUser = await verifyPayment({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              })
              updateUser(updatedUser)
              setSuccessPlan(planId)
            } catch {
              setError('Payment was received but verification failed. Contact support.')
            } finally {
              setLoading(null)
            }
          },
        }

        rzpRef.current = new window.Razorpay(options)
        rzpRef.current.open()
      } catch {
        setError('Could not initiate payment. Please try again.')
        setLoading(null)
      }
    },
    [annual, isAuthenticated, openAuthModal, scriptReady, updateUser],
  )

  return { checkout, loading, error, successPlan, setError }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function PricingPage() {
  const [annual, setAnnual] = useState(false)
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const { isAuthenticated } = useAuthStore()
  const { openAuthModal } = useUIStore()
  const { checkout, loading, error, successPlan, setError } = useRazorpayCheckout(annual)

  useEffect(() => { document.title = 'Pricing — PropIQ' }, [])

  const handleCta = (planId: string) => {
    if (planId === 'free') {
      if (!isAuthenticated) openAuthModal()
      return
    }
    checkout(planId as PlanId)
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      {/* Header */}
      <div className="text-center mb-10">
        <p className="text-propiq-teal font-semibold text-sm uppercase tracking-wide mb-2">Transparent pricing</p>
        <h1 className="text-3xl font-extrabold text-propiq-navy mb-3">
          Know before you invest.
        </h1>
        <p className="text-slate-500 max-w-xl mx-auto">
          Start free and upgrade when you need full due diligence. No hidden fees, no broker commissions.
        </p>

        {/* Annual toggle */}
        <div className="flex items-center justify-center gap-3 mt-6">
          <span className={`text-sm font-medium ${!annual ? 'text-propiq-navy' : 'text-slate-400'}`}>Monthly</span>
          <button
            onClick={() => setAnnual((v) => !v)}
            className={`relative w-11 h-6 rounded-full transition-colors ${annual ? 'bg-propiq-teal' : 'bg-slate-200'}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${annual ? 'translate-x-5' : ''}`}
            />
          </button>
          <span className={`text-sm font-medium ${annual ? 'text-propiq-navy' : 'text-slate-400'}`}>
            Annual
            <span className="ml-1.5 text-2xs font-bold text-propiq-teal bg-teal-50 border border-teal-200 rounded-full px-1.5 py-0.5">
              Save 20%
            </span>
          </span>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Success banner */}
      {successPlan && (
        <div className="mb-6 flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
          <CheckCircle size={16} className="shrink-0 text-green-500" />
          <span>
            You're now on the <strong className="capitalize">{successPlan}</strong> plan. Enjoy your upgraded access!
          </span>
        </div>
      )}

      {/* Pricing cards */}
      <div className="grid md:grid-cols-3 gap-6 mb-16">
        {PLANS.map((plan) => {
          const price = annual ? plan.annualPrice : plan.monthlyPrice
          const isPro = plan.id === 'pro'
          const isThisPlanLoading = loading === plan.id
          const isThisPlanSuccess = successPlan === plan.id

          return (
            <div
              key={plan.id}
              className={`relative rounded-3xl p-6 flex flex-col ${
                isPro
                  ? 'bg-propiq-gradient text-white shadow-2xl scale-[1.02]'
                  : 'bg-white shadow-card'
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-amber-400 text-white text-xs font-bold px-3 py-1 rounded-full shadow">
                  <Zap size={11} /> {plan.badge}
                </div>
              )}

              <div className="mb-5">
                <h2 className={`text-lg font-extrabold mb-0.5 ${isPro ? 'text-white' : 'text-propiq-navy'}`}>
                  {plan.name}
                </h2>
                <p className={`text-xs ${isPro ? 'text-white/70' : 'text-slate-500'}`}>{plan.description}</p>
              </div>

              <div className="mb-5">
                {price === 0 ? (
                  <p className={`text-4xl font-extrabold ${isPro ? 'text-white' : 'text-propiq-navy'}`}>Free</p>
                ) : (
                  <div className="flex items-end gap-1">
                    <span className={`text-3xl font-extrabold ${isPro ? 'text-white' : 'text-propiq-navy'}`}>
                      ₹{price.toLocaleString('en-IN')}
                    </span>
                    <span className={`text-sm mb-1 ${isPro ? 'text-white/70' : 'text-slate-500'}`}>/month</span>
                  </div>
                )}
                {annual && price > 0 && (
                  <p className={`text-xs mt-0.5 ${isPro ? 'text-white/60' : 'text-slate-400'}`}>
                    Billed ₹{(price * 12).toLocaleString('en-IN')} annually
                  </p>
                )}
              </div>

              <ul className="space-y-2.5 mb-6 flex-1">
                {plan.features.map(({ text, included }) => (
                  <li key={text} className="flex items-start gap-2 text-sm">
                    {included ? (
                      <CheckCircle2 size={15} className={`shrink-0 mt-0.5 ${isPro ? 'text-teal-300' : 'text-risk-low'}`} />
                    ) : (
                      <X size={15} className={`shrink-0 mt-0.5 ${isPro ? 'text-white/30' : 'text-slate-300'}`} />
                    )}
                    <span className={included
                      ? (isPro ? 'text-white/90' : 'text-slate-700')
                      : (isPro ? 'text-white/40 line-through' : 'text-slate-400')
                    }>
                      {text}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleCta(plan.id)}
                disabled={isThisPlanLoading || !!successPlan}
                className={`w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed ${
                  isPro
                    ? 'bg-white text-propiq-navy hover:bg-navy-50 shadow-lg'
                    : plan.ctaVariant === 'primary'
                    ? 'bg-propiq-navy text-white hover:bg-navy-700'
                    : 'border-2 border-propiq-navy/20 text-propiq-navy hover:border-propiq-navy hover:bg-propiq-navy/5'
                }`}
              >
                {isThisPlanLoading ? (
                  <><Loader2 size={14} className="animate-spin" /> Processing…</>
                ) : isThisPlanSuccess ? (
                  <><CheckCircle size={14} /> Active</>
                ) : (
                  plan.cta
                )}
              </button>
            </div>
          )
        })}
      </div>

      {/* FAQ */}
      <div className="max-w-2xl mx-auto">
        <h2 className="text-xl font-bold text-propiq-navy text-center mb-6">Frequently asked questions</h2>
        <div className="space-y-2">
          {FAQ.map(({ q, a }, i) => (
            <div key={i} className="bg-white rounded-2xl shadow-card overflow-hidden">
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="font-semibold text-sm text-propiq-navy">{q}</span>
                <span className={`text-slate-400 transition-transform ${openFaq === i ? 'rotate-180' : ''}`}>
                  ▾
                </span>
              </button>
              {openFaq === i && (
                <div className="px-5 pb-4">
                  <p className="text-sm text-slate-600 leading-relaxed">{a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
