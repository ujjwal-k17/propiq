import clsx from 'clsx'

export interface SkeletonProps {
  width?: string | number
  height?: string | number
  className?: string
  rounded?: 'sm' | 'md' | 'lg' | 'full'
}

export function Skeleton({ width, height, className, rounded = 'md' }: SkeletonProps) {
  const roundedMap = { sm: 'rounded', md: 'rounded-lg', lg: 'rounded-xl', full: 'rounded-full' }
  return (
    <div
      aria-hidden="true"
      className={clsx(
        'bg-gradient-to-r from-slate-100 via-slate-200 to-slate-100 bg-[length:200%_100%] animate-shimmer',
        roundedMap[rounded],
        className,
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  )
}

/** Pre-composed skeleton for a project card */
export function ProjectCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5 space-y-4">
      <div className="flex justify-between">
        <div className="space-y-2">
          <Skeleton width={180} height={20} />
          <Skeleton width={120} height={16} />
        </div>
        <Skeleton width={56} height={56} rounded="full" />
      </div>
      <Skeleton height={4} rounded="full" />
      <div className="flex gap-3">
        <Skeleton width={80} height={32} />
        <Skeleton width={80} height={32} />
        <Skeleton width={80} height={32} />
      </div>
    </div>
  )
}

/** Pre-composed skeleton for a list item */
export function ListItemSkeleton() {
  return (
    <div className="flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-100">
      <Skeleton width={44} height={44} rounded="full" />
      <div className="flex-1 space-y-2">
        <Skeleton width="60%" height={16} />
        <Skeleton width="40%" height={14} />
      </div>
      <Skeleton width={80} height={14} />
    </div>
  )
}
