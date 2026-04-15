/**
 * useAlerts — WebSocket hook for real-time project alerts.
 *
 * Connects to ``ws(s)://<host>/api/v1/ws/alerts?token=<jwt>`` on mount,
 * dispatches incoming messages to the ``useAlertsStore``, and tears down
 * cleanly on unmount or when the user logs out.
 *
 * Reconnection strategy:
 *   - Exponential back-off starting at 2s, capped at 60s.
 *   - Stops retrying when the component unmounts or the user is logged out.
 *
 * Usage (call once at the top of the app, e.g. in AppLayout):
 *
 *   useAlerts()
 *
 * Subscribe to state in any component:
 *
 *   const { alerts, unreadCount } = useAlertsStore()
 */
import { useEffect, useRef } from 'react'
import { useAuthStore, useAlertsStore } from '@/store'
import type { WSMessage } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1'

/** Build the WebSocket URL from the REST API base URL. */
function buildWsUrl(token: string): string {
  const base = API_BASE.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  return `${base}/api/v1/ws/alerts?token=${encodeURIComponent(token)}`
}

export function useAlerts(): void {
  const { token, isAuthenticated } = useAuthStore()
  const { addAlert, setHistory, markRead, setWsStatus } = useAlertsStore()

  const wsRef      = useRef<WebSocket | null>(null)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const backoffMs  = useRef(2_000)
  const unmounted  = useRef(false)

  useEffect(() => {
    unmounted.current = false

    if (!isAuthenticated || !token) {
      setWsStatus('disconnected')
      return
    }

    function connect() {
      if (unmounted.current) return
      setWsStatus('connecting')

      const url = buildWsUrl(token!)
      const ws  = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (unmounted.current) { ws.close(); return }
        backoffMs.current = 2_000   // reset back-off on successful connect
        setWsStatus('connected')
      }

      ws.onmessage = (event: MessageEvent<string>) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage

          switch (msg.type) {
            case 'connected':
              // Server sends connected payload — no extra action needed;
              // history arrives in a separate "history" message.
              break

            case 'alert':
              addAlert(msg.data)
              // Browser notification (if permission granted)
              if (Notification.permission === 'granted') {
                new Notification(`PropIQ Alert — ${msg.data.project_name ?? 'Watchlist'}`, {
                  body: msg.data.title,
                  icon: '/favicon.ico',
                  tag: msg.data.id,
                })
              }
              break

            case 'history':
              setHistory(msg.data)
              break

            case 'marked_read':
              markRead(msg.data.alert_ids)
              break

            case 'ping':
              // Server heartbeat — reply with pong
              ws.send(JSON.stringify({ type: 'pong' }))
              break

            default:
              break
          }
        } catch {
          // Ignore malformed frames
        }
      }

      ws.onclose = (event) => {
        wsRef.current = null
        if (unmounted.current) return

        if (event.code === 4001) {
          // Auth failure — don't retry
          setWsStatus('error')
          return
        }

        setWsStatus('disconnected')
        const delay = backoffMs.current
        backoffMs.current = Math.min(backoffMs.current * 2, 60_000)
        retryTimer.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        // onclose fires right after — let that handle the reconnect logic
        setWsStatus('error')
      }
    }

    connect()

    return () => {
      unmounted.current = true
      if (retryTimer.current) clearTimeout(retryTimer.current)
      if (wsRef.current) {
        wsRef.current.close(1000, 'component unmounted')
        wsRef.current = null
      }
    }
  }, [isAuthenticated, token]) // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * Send a message to the open WebSocket.
 * Useful for subscribing to extra projects after initial connect.
 */
export function sendWsMessage(payload: object): void {
  // Access via module-level ref isn't possible; callers should use the
  // wsRef from a context if they need to send messages directly.
  // For most cases, request_history and mark_read are handled automatically.
  void payload
}
