/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        warmBg: 'var(--bg-app)',
        surface: {
          DEFAULT: 'var(--surface)',
          subtle: 'var(--surface-subtle)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          secondary: 'var(--ink-secondary)',
          muted: 'var(--ink-muted)',
        },
        stoneBorder: {
          DEFAULT: 'var(--border-stone)',
          strong: 'var(--border-stone-strong)',
        },
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          tint: 'var(--primary-tint)',
          light: 'var(--primary-tint)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          tint: 'var(--accent-tint)',
          light: 'var(--accent-tint)',
        },
        status: {
          verified: 'var(--status-verified)',
          'verified-bg': 'var(--status-verified-bg)',
          'verified-text': 'var(--status-verified-text)',
          
          needsVerification: 'var(--status-needs-verification)',
          'needsVerification-bg': 'var(--status-needs-verification-bg)',
          'needsVerification-text': 'var(--status-needs-verification-text)',
          
          inconsistent: 'var(--status-inconsistent)',
          'inconsistent-bg': 'var(--status-inconsistent-bg)',
          'inconsistent-text': 'var(--status-inconsistent-text)',
          
          tampering: 'var(--status-tampering)',
          'tampering-bg': 'var(--status-tampering-bg)',
          'tampering-text': 'var(--status-tampering-text)',
          
          info: 'var(--status-info)',
          'info-bg': 'var(--status-info-bg)',
          'info-text': 'var(--status-info-text)',

          neutral: 'var(--status-info)',
          'neutral-bg': 'var(--status-info-bg)',
          'neutral-text': 'var(--status-info-text)',
        },
        risk: {
          low: 'var(--status-verified)',
          'low-bg': 'var(--status-verified-bg)',
          'low-text': 'var(--status-verified-text)',
          medium: 'var(--status-needs-verification)',
          'medium-bg': 'var(--status-needs-verification-bg)',
          'medium-text': 'var(--status-needs-verification-text)',
          high: 'var(--status-inconsistent)',
          'high-bg': 'var(--status-inconsistent-bg)',
          'high-text': 'var(--status-inconsistent-text)',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
        hindi: ['"Noto Sans Devanagari"', 'sans-serif'],
      },
      fontSize: {
        'xs': ['12px', '16px'],
        'sm': ['14px', '20px'],
        'base': ['16px', '24px'],
        'lg': ['18px', '26px'],
        'xl': ['20px', '28px'],
        '2xl': ['24px', '32px'],
        '3xl': ['32px', '40px'],
        '4xl': ['40px', '48px'],
      },
      borderRadius: {
        'input': '6px',
        'card': '12px',
        'full': '999px',
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        'modal': '0 10px 25px -5px rgba(30, 58, 95, 0.12), 0 8px 10px -6px rgba(30, 58, 95, 0.08)',
      },
    },
  },
  plugins: [],
}
