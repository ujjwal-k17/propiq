import { useEffect, useState } from 'react'

export interface ScoreGaugeProps {
  score: number
  size?: number
  label?: string
}

function bandColor(score: number): string {
  if (score >= 80) return '#15803d'
  if (score >= 60) return '#b45309'
  if (score >= 40) return '#c2410c'
  return '#b91c1c'
}

export function ScoreGauge({ score, size = 120, label }: ScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0)

  useEffect(() => {
    // Animate from 0 to score over 800ms
    const start = performance.now()
    const duration = 800
    const target = Math.min(100, Math.max(0, score))

    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / duration)
      // ease-out cubic
      const eased = 1 - (1 - progress) ** 3
      setAnimatedScore(Math.round(eased * target))
      if (progress < 1) requestAnimationFrame(step)
    }

    const raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [score])

  const strokeWidth = size * 0.1
  const cx = size / 2
  const cy = size / 2
  const r = (size - strokeWidth * 2) / 2

  // Full circumference and half-arc (for semicircle)
  const circumference = 2 * Math.PI * r
  const semiArc = circumference / 2

  // Filled portion
  const filled = (animatedScore / 100) * semiArc

  // Needle angle: score=0 → left (π radians), score=100 → right (0 radians)
  const needleAngle = Math.PI * (1 - animatedScore / 100)
  const needleLen = r * 0.75
  const nx = cx + needleLen * Math.cos(needleAngle)
  const ny = cy - needleLen * Math.sin(needleAngle)

  const color = bandColor(animatedScore)

  // Unique IDs for gradient (avoids conflicts on page with multiple gauges)
  const gradId = `gauge-grad-${size}-${Math.round(score)}`

  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`Score: ${score} out of 100`}>
      <svg
        width={size}
        height={size / 2 + strokeWidth * 1.5}
        viewBox={`0 0 ${size} ${size / 2 + strokeWidth * 1.5}`}
        overflow="visible"
      >
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#b91c1c" />
            <stop offset="33%"  stopColor="#c2410c" />
            <stop offset="66%"  stopColor="#b45309" />
            <stop offset="100%" stopColor="#15803d" />
          </linearGradient>
        </defs>

        {/* Background arc — full semicircle */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
          strokeDasharray={`${semiArc} ${circumference}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform={`rotate(180, ${cx}, ${cy})`}
        />

        {/* Score arc */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={0}
          strokeLinecap="round"
          transform={`rotate(180, ${cx}, ${cy})`}
          style={{ transition: 'stroke-dasharray 0.05s' }}
        />

        {/* Needle */}
        <line
          x1={cx} y1={cy}
          x2={nx} y2={ny}
          stroke={color}
          strokeWidth={strokeWidth * 0.3}
          strokeLinecap="round"
        />

        {/* Center dot */}
        <circle cx={cx} cy={cy} r={strokeWidth * 0.35} fill={color} />

        {/* Score text */}
        <text
          x={cx} y={cy - 4}
          textAnchor="middle"
          dominantBaseline="auto"
          fontFamily="JetBrains Mono, monospace"
          fontWeight="800"
          fontSize={size * 0.18}
          fill={color}
        >
          {animatedScore}
        </text>
        <text
          x={cx} y={cy + size * 0.06}
          textAnchor="middle"
          dominantBaseline="hanging"
          fontFamily="JetBrains Mono, monospace"
          fontWeight="500"
          fontSize={size * 0.1}
          fill="#94a3b8"
        >
          / 100
        </text>
      </svg>

      {label && (
        <p className="text-xs text-slate-500 font-medium text-center">{label}</p>
      )}
    </div>
  )
}
