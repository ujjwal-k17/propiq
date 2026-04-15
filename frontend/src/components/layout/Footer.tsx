import { Link } from 'react-router-dom'
import { Shield, ExternalLink } from 'lucide-react'

const LINKS = {
  Company: [
    { label: 'About PropIQ', to: '/about' },
    { label: 'How It Works', to: '/how-it-works' },
    { label: 'Pricing', to: '/pricing' },
    { label: 'Contact', to: '/contact' },
  ],
  Resources: [
    { label: 'RERA Portal', href: 'https://rera.gov.in', external: true },
    { label: 'MCA21', href: 'https://www.mca.gov.in', external: true },
    { label: 'NHB', href: 'https://nhb.org.in', external: true },
  ],
  Legal: [
    { label: 'Privacy Policy', to: '/privacy' },
    { label: 'Terms of Service', to: '/terms' },
    { label: 'Disclaimer', to: '/disclaimer' },
  ],
}

export function Footer() {
  return (
    <footer className="bg-propiq-navy text-white mt-20">
      <div className="max-w-7xl mx-auto px-4 py-14">
        {/* Top: logo + columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="flex items-center gap-2 font-bold text-lg mb-3">
              <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
                <Shield size={15} />
              </div>
              PropIQ
            </Link>
            <p className="text-sm text-navy-200 leading-relaxed max-w-xs">
              AI-powered real estate due diligence for Indian property buyers and investors.
              Know before you invest.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([section, items]) => (
            <div key={section}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-navy-300 mb-3">
                {section}
              </h4>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li key={item.label}>
                    {'href' in item ? (
                      <a
                        href={item.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-navy-200 hover:text-white transition-colors flex items-center gap-1"
                      >
                        {item.label}
                        {'external' in item && <ExternalLink size={10} />}
                      </a>
                    ) : (
                      <Link
                        to={item.to}
                        className="text-sm text-navy-200 hover:text-white transition-colors"
                      >
                        {item.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Disclaimer */}
        <div className="border-t border-white/10 pt-8">
          <p className="text-xs text-navy-300 leading-relaxed mb-4 max-w-4xl">
            <strong className="text-navy-100">Disclaimer:</strong> PropIQ scores and reports are generated
            algorithmically from publicly available data (RERA, MCA21, news sources) and are provided for
            informational purposes only. They do not constitute financial, legal, or investment advice.
            Real estate investments involve significant risk. Always consult a SEBI-registered investment
            advisor and qualified legal counsel before making any investment decision. PropIQ is not liable
            for any financial loss arising from decisions made based on information provided on this platform.
          </p>
          <p className="text-xs text-navy-400">
            © {new Date().getFullYear()} PropIQ Technologies Pvt. Ltd. All rights reserved.
            Data sourced from RERA portals, MCA21, and public records.
          </p>
        </div>
      </div>
    </footer>
  )
}
