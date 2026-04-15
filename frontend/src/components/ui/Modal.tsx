import {
  useEffect,
  useRef,
  type ReactNode,
  type KeyboardEvent,
} from 'react'
import { X } from 'lucide-react'
import clsx from 'clsx'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  hideHeader?: boolean
}

const sizeMap = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}

export function Modal({ isOpen, onClose, title, children, size = 'md', hideHeader = false }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const lastFocusedRef = useRef<HTMLElement | null>(null)

  // Restore focus on close, lock body scroll while open
  useEffect(() => {
    if (isOpen) {
      lastFocusedRef.current = document.activeElement as HTMLElement
      document.body.style.overflow = 'hidden'
      // Move focus inside dialog after render
      requestAnimationFrame(() => {
        const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        firstFocusable?.focus()
      })
    } else {
      document.body.style.overflow = ''
      lastFocusedRef.current?.focus()
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  // Escape key
  useEffect(() => {
    const handle = (e: globalThis.KeyboardEvent) => {
      if (isOpen && e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handle)
    return () => document.removeEventListener('keydown', handle)
  }, [isOpen, onClose])

  // Focus trap
  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'Tab') return
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusable || focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey) {
      if (document.activeElement === first) { last.focus(); e.preventDefault() }
    } else {
      if (document.activeElement === last) { first.focus(); e.preventDefault() }
    }
  }

  if (!isOpen) return null

  return (
    <div
      aria-modal="true"
      role="dialog"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        onKeyDown={handleKeyDown}
        className={clsx(
          'relative w-full bg-white rounded-2xl shadow-2xl animate-fade-in z-10',
          sizeMap[size],
        )}
      >
        {!hideHeader && (
          <div className="flex items-center justify-between p-5 border-b border-slate-100">
            {title && (
              <h2 className="text-lg font-semibold text-propiq-navy">{title}</h2>
            )}
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="ml-auto p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy"
            >
              <X size={18} />
            </button>
          </div>
        )}
        <div className={hideHeader ? 'p-5' : 'p-5 pt-4'}>{children}</div>
      </div>
    </div>
  )
}
