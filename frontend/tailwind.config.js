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
        surface: 'var(--surface)',
        stoneBorder: 'var(--border-stone)',
        stoneBorderStrong: 'var(--border-stone-strong)',
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          light: 'var(--primary-light)',
          text: 'var(--primary-text)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          light: 'var(--accent-light)',
          text: 'var(--accent-text)',
        },
        status: {
          verified: 'var(--status-verified)',
          'verified-bg': 'var(--status-verified-bg)',
          'verified-border': 'var(--status-verified-border)',
          'verified-text': 'var(--status-verified-text)',
          
          needsVerification: 'var(--status-needs-verification)',
          'needsVerification-bg': 'var(--status-needs-verification-bg)',
          'needsVerification-border': 'var(--status-needs-verification-border)',
          'needsVerification-text': 'var(--status-needs-verification-text)',
          
          inconsistent: 'var(--status-inconsistent)',
          'inconsistent-bg': 'var(--status-inconsistent-bg)',
          'inconsistent-border': 'var(--status-inconsistent-border)',
          'inconsistent-text': 'var(--status-inconsistent-text)',
          
          tampering: 'var(--status-tampering)',
          'tampering-bg': 'var(--status-tampering-bg)',
          'tampering-border': 'var(--status-tampering-border)',
          'tampering-text': 'var(--status-tampering-text)',
          
          neutral: 'var(--status-neutral)',
          'neutral-bg': 'var(--status-neutral-bg)',
          'neutral-border': 'var(--status-neutral-border)',
          'neutral-text': 'var(--status-neutral-text)',
        },
        risk: {
          low: 'var(--risk-low)',
          'low-bg': 'var(--risk-low-bg)',
          'low-text': 'var(--risk-low-text)',
          medium: 'var(--risk-medium)',
          'medium-bg': 'var(--risk-medium-bg)',
          'medium-text': 'var(--risk-medium-text)',
          high: 'var(--risk-high)',
          'high-bg': 'var(--risk-high-bg)',
          'high-text': 'var(--risk-high-text)',
        }
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        devanagari: ['"Noto Sans Devanagari"', '"IBM Plex Sans"', 'sans-serif'],
      },
      fontSize: {
        'xs': ['12px', { lineHeight: '18px' }],
        'sm': ['14px', { lineHeight: '21px' }],
        'base': ['16px', { lineHeight: '24px' }],
        'xl': ['20px', { lineHeight: '28px' }],
        '2xl': ['24px', { lineHeight: '32px' }],
        '3xl': ['32px', { lineHeight: '40px' }],
      },
      borderRadius: {
        'sm': '4px',
        'DEFAULT': '6px',
        'md': '6px',
        'lg': '10px',
        'xl': '12px',
      },
      maxWidth: {
        'content': '1280px',
      },
      boxShadow: {
        'overlay': '0 4px 20px -2px rgba(30, 58, 95, 0.08), 0 2px 6px -1px rgba(30, 58, 95, 0.04)',
        'modal': '0 10px 30px -4px rgba(30, 58, 95, 0.12), 0 4px 10px -2px rgba(30, 58, 95, 0.06)',
      },
      transitionDuration: {
        'DEFAULT': '150ms',
      }
    },
  },
  plugins: [],
}
