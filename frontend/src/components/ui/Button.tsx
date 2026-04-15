import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

const base =
  'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none'

const variants = {
  primary:
    'bg-propiq-navy text-white hover:bg-navy-600 active:bg-navy-700 focus-visible:ring-propiq-navy shadow-sm',
  secondary:
    'border-2 border-propiq-navy text-propiq-navy bg-transparent hover:bg-navy-50 active:bg-navy-100 focus-visible:ring-propiq-navy',
  ghost:
    'text-propiq-navy bg-transparent hover:bg-navy-50 active:bg-navy-100 focus-visible:ring-propiq-navy',
  danger:
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus-visible:ring-red-600 shadow-sm',
}

const sizes = {
  sm: 'text-xs px-3 py-1.5 h-8',
  md: 'text-sm px-4 py-2 h-10',
  lg: 'text-base px-6 py-3 h-12',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      className,
      children,
      ...rest
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        aria-disabled={disabled || loading}
        aria-busy={loading}
        className={clsx(base, variants[variant], sizes[size], className)}
        {...rest}
      >
        {loading ? (
          <Loader2 size={size === 'lg' ? 18 : 16} className="animate-spin shrink-0" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children}
        {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    )
  },
)
Button.displayName = 'Button'
