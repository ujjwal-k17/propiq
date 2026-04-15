import clsx from 'clsx'

type BadgeColor = 'green' | 'blue' | 'teal' | 'orange' | 'red' | 'gray' | 'amber'

export interface BadgeProps {
  label: string
  color?: BadgeColor
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
}

const colorMap: Record<BadgeColor, string> = {
  green:  'bg-green-50 text-green-800 border-green-200',
  blue:   'bg-blue-50 text-blue-800 border-blue-200',
  teal:   'bg-teal-50 text-propiq-teal border-teal-200',
  orange: 'bg-orange-50 text-orange-800 border-orange-200',
  red:    'bg-red-50 text-red-800 border-red-200',
  gray:   'bg-gray-100 text-gray-700 border-gray-200',
  amber:  'bg-amber-50 text-amber-800 border-amber-200',
}

const dotColorMap: Record<BadgeColor, string> = {
  green:  'bg-green-500',
  blue:   'bg-blue-500',
  teal:   'bg-propiq-teal',
  orange: 'bg-orange-500',
  red:    'bg-red-500',
  gray:   'bg-gray-400',
  amber:  'bg-amber-500',
}

export function Badge({ label, color = 'gray', size = 'sm', dot = false, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium border rounded-full',
        size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1',
        colorMap[color],
        className,
      )}
    >
      {dot && (
        <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', dotColorMap[color])} />
      )}
      {label}
    </span>
  )
}
