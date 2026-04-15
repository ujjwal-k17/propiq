/**
 * AlertBell — notification bell icon with unread badge.
 *
 * Clicking it toggles the AlertPanel.
 * Shows a colored dot for critical / warning alerts and a numeric badge
 * for up to 99+ unread items.
 */
import { Bell, BellRing } from 'lucide-react'
import { useAlertsStore } from '@/store'
import type { AlertSeverity } from '@/types'

export interface AlertBellProps {
  /** Controls whether the panel is open (lifted state from Navbar). */
  open: boolean
  onToggle: () => void
}

function badgeColor(alerts: { severity: AlertSeverity; id: string }[], readIds: Set<string>): string {
  const unread = alerts.filter((a) => !readIds.has(a.id))
  if (unread.some((a) => a.severity === 'critical')) return 'bg-red-500'
  if (unread.some((a) => a.severity === 'warning'))  return 'bg-amber-500'
  return 'bg-propiq-blue'
}

export function AlertBell({ open, onToggle }: AlertBellProps) {
  const { alerts, readIds, unreadCount, wsStatus } = useAlertsStore()
  const count  = unreadCount()
  const hasNew = count > 0

  return (
    <button
      onClick={onToggle}
      aria-label={`Notifications${hasNew ? ` (${count} unread)` : ''}`}
      aria-expanded={open}
      className={`
        relative p-2 rounded-lg transition-colors
        ${open
          ? 'bg-slate-100 text-propiq-navy'
          : 'text-slate-500 hover:text-propiq-navy hover:bg-slate-50'
        }
      `}
    >
      {/* Animated bell when there are unread alerts */}
      {hasNew
        ? <BellRing size={18} className="animate-[ring_1s_ease-in-out]" />
        : <Bell size={18} />
      }

      {/* Numeric badge */}
      {hasNew && (
        <span
          className={`
            absolute -top-0.5 -right-0.5
            min-w-[16px] h-4 px-1
            ${badgeColor(alerts, readIds)}
            text-white text-[10px] font-bold leading-4
            rounded-full flex items-center justify-center
          `}
        >
          {count > 99 ? '99+' : count}
        </span>
      )}

      {/* WebSocket connection indicator dot */}
      <span
        className={`
          absolute bottom-1 right-1 w-1.5 h-1.5 rounded-full
          ${wsStatus === 'connected'
            ? 'bg-green-400'
            : wsStatus === 'connecting'
            ? 'bg-amber-400 animate-pulse'
            : 'bg-slate-300'
          }
        `}
        title={`Alerts: ${wsStatus}`}
      />
    </button>
  )
}
