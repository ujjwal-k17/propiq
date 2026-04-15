/**
 * AlertPanel — slide-in notification drawer.
 *
 * Renders above the Navbar (z-60) on mobile, to the right of the bell
 * on desktop.  Displays the 100 most recent alerts with severity badges,
 * project links, and a "Mark all read" button.
 */
import { useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  X, CheckCheck, AlertTriangle, Info, Zap,
  Shield, TrendingDown, Building2, Calendar,
  WifiOff,
} from 'lucide-react'
import { useAlertsStore } from '@/store'
import { useAuthStore } from '@/store'
import { apiClient } from '@/services/api'
import type { AlertSeverity, AlertType, ProjectAlert } from '@/types'
import { formatDate } from '@/utils/formatters'

// ── Severity styling ──────────────────────────────────────────────────────────

const SEVERITY_STYLE: Record<AlertSeverity, { border: string; bg: string; text: string; dot: string }> = {
  info:     { border: 'border-blue-100',  bg: 'bg-blue-50',  text: 'text-blue-700',  dot: 'bg-blue-400' },
  warning:  { border: 'border-amber-100', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-400' },
  critical: { border: 'border-red-100',   bg: 'bg-red-50',   text: 'text-red-700',   dot: 'bg-red-500' },
}

// ── Alert type icons ──────────────────────────────────────────────────────────

function AlertIcon({ type, severity }: { type: AlertType; severity: AlertSeverity }) {
  const cls = `w-4 h-4 flex-shrink-0 ${SEVERITY_STYLE[severity].text}`
  switch (type) {
    case 'rera_status_change':    return <Shield className={cls} />
    case 'new_complaint':         return <AlertTriangle className={cls} />
    case 'possession_date_delay': return <Calendar className={cls} />
    case 'construction_milestone':return <Building2 className={cls} />
    case 'risk_band_change':      return <TrendingDown className={cls} />
    case 'developer_nclt':        return <Zap className={cls} />
    default:                       return <Info className={cls} />
  }
}

// ── Single alert row ──────────────────────────────────────────────────────────

function AlertRow({ alert, onMarkRead }: { alert: ProjectAlert; onMarkRead: (id: string) => void }) {
  const { readIds } = useAlertsStore()
  const isRead = readIds.has(alert.id)
  const style  = SEVERITY_STYLE[alert.severity]

  return (
    <div
      className={`
        relative flex gap-3 px-4 py-3 border-b border-slate-100
        ${isRead ? 'opacity-60' : ''}
        hover:bg-slate-50 transition-colors group
      `}
    >
      {/* Unread indicator */}
      {!isRead && (
        <span className={`absolute left-2 top-4 w-1.5 h-1.5 rounded-full ${style.dot}`} />
      )}

      {/* Icon */}
      <div className={`mt-0.5 p-1.5 rounded-lg ${style.bg} ${style.border} border`}>
        <AlertIcon type={alert.alert_type} severity={alert.severity} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={`text-xs font-semibold leading-snug ${style.text}`}>{alert.title}</p>
          <span className="text-[10px] text-slate-400 whitespace-nowrap flex-shrink-0">
            {formatDate(alert.created_at)}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{alert.message}</p>
        {alert.project_name && (
          <Link
            to={`/projects/${alert.project_id}`}
            className="mt-1 inline-block text-[11px] text-propiq-blue hover:underline font-medium"
          >
            {alert.project_name} →
          </Link>
        )}
      </div>

      {/* Mark-read button (hover) */}
      {!isRead && (
        <button
          onClick={(e) => { e.stopPropagation(); onMarkRead(alert.id) }}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-propiq-blue self-start mt-0.5"
          title="Mark as read"
        >
          <CheckCheck size={13} />
        </button>
      )}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
      <CheckCheck size={32} className="mb-3 text-slate-200" />
      <p className="text-sm font-medium">You're all caught up</p>
      <p className="text-xs mt-1">Alerts appear here when we detect changes</p>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export interface AlertPanelProps {
  open: boolean
  onClose: () => void
}

export function AlertPanel({ open, onClose }: AlertPanelProps) {
  const { alerts, readIds, wsStatus, markRead, markAllRead } = useAlertsStore()
  const { token } = useAuthStore()
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handle = (e: MouseEvent) => {
      if (!panelRef.current?.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [open, onClose])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [open, onClose])

  async function handleMarkRead(id: string) {
    markRead([id])
    if (token) {
      try {
        await apiClient.post('/ws/mark_read', { alert_ids: [id] })
      } catch {
        // best-effort
      }
    }
  }

  async function handleMarkAllRead() {
    const unreadIds = alerts.filter((a) => !readIds.has(a.id)).map((a) => a.id)
    markAllRead()
    if (token && unreadIds.length) {
      try {
        await apiClient.post('/ws/mark_read', { alert_ids: unreadIds })
      } catch {
        // best-effort
      }
    }
  }

  const unreadCount = alerts.filter((a) => !readIds.has(a.id)).length

  if (!open) return null

  return (
    <>
      {/* Mobile backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40 md:hidden" onClick={onClose} />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Notifications"
        className={`
          fixed md:absolute
          inset-x-0 bottom-0 md:inset-auto
          md:right-0 md:top-full md:mt-2
          z-50
          w-full md:w-96
          bg-white
          rounded-t-2xl md:rounded-2xl
          border border-slate-200
          shadow-card-hover
          flex flex-col
          max-h-[80vh] md:max-h-[520px]
          animate-fade-in
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 flex-shrink-0">
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-sm text-propiq-navy">Alerts</h2>
            {unreadCount > 0 && (
              <span className="bg-propiq-blue text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
            {wsStatus !== 'connected' && (
              <span className="flex items-center gap-1 text-[10px] text-slate-400">
                <WifiOff size={10} />
                {wsStatus}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-xs text-propiq-blue hover:text-propiq-navy px-2 py-1 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <CheckCheck size={12} /> Mark all read
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Close notifications"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Alert list */}
        <div className="overflow-y-auto flex-1 min-h-0">
          {alerts.length === 0
            ? <EmptyState />
            : alerts.map((alert) => (
                <AlertRow key={alert.id} alert={alert} onMarkRead={handleMarkRead} />
              ))
          }
        </div>

        {/* Footer */}
        {alerts.length > 0 && (
          <div className="px-4 py-2.5 border-t border-slate-100 flex-shrink-0 text-center">
            <p className="text-[11px] text-slate-400">
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''} · real-time via WebSocket
            </p>
          </div>
        )}
      </div>
    </>
  )
}
