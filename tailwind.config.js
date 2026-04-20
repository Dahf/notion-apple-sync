/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        cream: {
          50:  '#faf9f5',
          100: '#f5f4ed',
          200: '#eae5db',
          300: '#ddd6c8',
          400: '#c4bba9',
        },
        ink: {
          900: '#1a1613',
          800: '#2a241f',
          700: '#3d3631',
          600: '#524940',
          500: '#6b635a',
          400: '#8a8178',
          300: '#aea59a',
        },
        rust: {
          50:  '#faf0eb',
          100: '#f5e4d9',
          200: '#ead0bd',
          300: '#dcae8f',
          400: '#ca8865',
          500: '#bd5d3a',
          600: '#a54e30',
          700: '#8a3f26',
          800: '#6b301e',
        },
      },
      fontFamily: {
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans:  ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono:  ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        'tight-display': '-0.02em',
      },
      boxShadow: {
        'paper': '0 1px 2px rgba(26,22,19,0.04), 0 8px 32px -8px rgba(26,22,19,0.06)',
        'lift': '0 2px 4px rgba(26,22,19,0.04), 0 16px 48px -12px rgba(26,22,19,0.12)',
        'inset-hairline': 'inset 0 0 0 1px rgba(26,22,19,0.06)',
      },
    }
  },
  plugins: [],
}
