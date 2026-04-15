import {
  forwardRef,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
} from 'react'
import clsx from 'clsx'

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = {
  sm: { wrap: 'h-9',  input: 'text-sm',  label: 'text-xs top-2',   floated: '-translate-y-3.5 scale-90' },
  md: { wrap: 'h-11', input: 'text-sm',  label: 'text-sm top-3',   floated: '-translate-y-4 scale-90' },
  lg: { wrap: 'h-13', input: 'text-base', label: 'text-base top-3.5', floated: '-translate-y-5 scale-90' },
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      hint,
      leftIcon,
      rightIcon,
      size = 'md',
      className,
      id,
      placeholder,
      value,
      defaultValue,
      onFocus,
      onBlur,
      ...rest
    },
    ref,
  ) => {
    const [focused, setFocused] = useState(false)
    const inputId = id ?? `input-${Math.random().toString(36).slice(2)}`
    const errorId = `${inputId}-error`
    const hintId = `${inputId}-hint`

    // Label floats when focused OR has content
    const isFloated = focused || !!value || !!defaultValue || !!placeholder

    const { wrap, input, label: labelCls, floated } = sizeMap[size]

    return (
      <div className={clsx('flex flex-col gap-1', className)}>
        <div
          className={clsx(
            'relative border rounded-lg transition-all duration-150',
            wrap,
            error
              ? 'border-red-400 focus-within:ring-2 focus-within:ring-red-300'
              : 'border-slate-300 focus-within:border-propiq-blue focus-within:ring-2 focus-within:ring-propiq-blue/20',
          )}
        >
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              {leftIcon}
            </span>
          )}

          {label && (
            <label
              htmlFor={inputId}
              className={clsx(
                'absolute left-0 pointer-events-none transition-all duration-150 text-slate-500 origin-left',
                leftIcon ? 'left-10' : 'left-3',
                labelCls,
                isFloated && [floated, 'text-propiq-blue font-medium'],
                error && isFloated && '!text-red-500',
              )}
            >
              {label}
            </label>
          )}

          <input
            ref={ref}
            id={inputId}
            value={value}
            defaultValue={defaultValue}
            placeholder={!label ? placeholder : focused ? placeholder : undefined}
            aria-invalid={!!error}
            aria-describedby={
              [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined
            }
            className={clsx(
              'w-full h-full bg-transparent focus:outline-none',
              input,
              label ? 'pt-4 pb-1' : 'py-2',
              leftIcon ? 'pl-10' : 'pl-3',
              rightIcon ? 'pr-10' : 'pr-3',
              'text-slate-900 placeholder:text-slate-400',
            )}
            onFocus={(e) => { setFocused(true); onFocus?.(e) }}
            onBlur={(e) => { setFocused(false); onBlur?.(e) }}
            {...rest}
          />

          {rightIcon && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              {rightIcon}
            </span>
          )}
        </div>

        {error && (
          <p id={errorId} role="alert" className="text-xs text-red-600 flex items-center gap-1">
            <span aria-hidden="true">⚠</span> {error}
          </p>
        )}
        {!error && hint && (
          <p id={hintId} className="text-xs text-slate-500">{hint}</p>
        )}
      </div>
    )
  },
)
Input.displayName = 'Input'
