import { type MouseEvent, type KeyboardEvent, type ReactNode } from 'react'
import clsx from 'clsx'

export interface CardProps {
  children: ReactNode
  className?: string
  /** Lift shadow on hover */
  hoverable?: boolean
  /** Makes card behave as a button */
  onClick?: (e: MouseEvent<HTMLDivElement>) => void
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingMap = {
  none: '',
  sm:   'p-3',
  md:   'p-4 sm:p-6',
  lg:   'p-6 sm:p-8',
}

export function Card({
  children,
  className,
  hoverable = false,
  onClick,
  padding = 'md',
}: CardProps) {
  const isInteractive = hoverable || !!onClick

  const handleKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault()
      onClick(e as unknown as MouseEvent<HTMLDivElement>)
    }
  }

  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? handleKey : undefined}
      className={clsx(
        'bg-white rounded-2xl border border-slate-100',
        paddingMap[padding],
        isInteractive
          ? 'shadow-card transition-all duration-200 hover:shadow-card-hover'
          : 'shadow-card',
        onClick && 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-propiq-navy focus-visible:ring-offset-2',
        isInteractive && 'hover:-translate-y-0.5',
        className,
      )}
    >
      {children}
    </div>
  )
}
