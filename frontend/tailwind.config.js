/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],

  theme: {
    extend: {
      // ── Brand colors ────────────────────────────────────────────────────────
      colors: {
        'propiq-navy':  '#1A3A5C',
        'propiq-blue':  '#2E6DA4',
        'propiq-teal':  '#0E7C6B',

        // Risk band semantic colors
        'risk-low':      '#15803d',
        'risk-medium':   '#b45309',
        'risk-high':     '#c2410c',
        'risk-critical': '#b91c1c',

        // Surface colors
        'surface':       '#F4F7FB',
        'surface-card':  '#FFFFFF',

        // Shades used in PropIQ cards / data tables
        navy: {
          50:  '#eef2f7',
          100: '#d4e0ec',
          200: '#a9c1d9',
          300: '#7ea2c6',
          400: '#5383b3',
          500: '#2E6DA4',
          600: '#2a6292',
          700: '#1A3A5C',
          800: '#122741',
          900: '#0b1826',
        },
        teal: {
          50:  '#e6f4f2',
          100: '#c0e4e0',
          200: '#80c9bd',
          300: '#40ae9b',
          400: '#0e9380',
          500: '#0E7C6B',
          600: '#0b6357',
          700: '#084a41',
          800: '#05322c',
          900: '#031916',
        },
      },

      // ── Typography ──────────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },

      // ── Font size scale extension ────────────────────────────────────────────
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },

      // ── Shadows ─────────────────────────────────────────────────────────────
      boxShadow: {
        card:    '0 1px 4px rgba(26,58,92,0.08), 0 4px 16px rgba(26,58,92,0.06)',
        'card-hover': '0 4px 12px rgba(26,58,92,0.12), 0 12px 32px rgba(26,58,92,0.10)',
        score:   '0 0 0 3px rgba(14,124,107,0.25)',
      },

      // ── Border radius ────────────────────────────────────────────────────────
      borderRadius: {
        xl:  '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },

      // ── Animation ────────────────────────────────────────────────────────────
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'score-fill': {
          from: { width: '0%' },
        },
      },
      animation: {
        shimmer:    'shimmer 1.6s linear infinite',
        'fade-in':  'fade-in 0.2s ease-out',
        'score-fill': 'score-fill 0.8s ease-out forwards',
      },

      // ── Background gradients (used in hero / score ring) ──────────────────
      backgroundImage: {
        'propiq-gradient': 'linear-gradient(135deg, #1A3A5C 0%, #2E6DA4 60%, #0E7C6B 100%)',
        'score-low':      'linear-gradient(90deg, #15803d, #16a34a)',
        'score-medium':   'linear-gradient(90deg, #b45309, #d97706)',
        'score-high':     'linear-gradient(90deg, #c2410c, #ea580c)',
        'score-critical': 'linear-gradient(90deg, #b91c1c, #dc2626)',
        shimmer:          'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
      },
    },
  },

  plugins: [],
}
