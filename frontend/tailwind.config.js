/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta del diseño de referencia
        primary: {
          50:  '#f0fdf9',
          100: '#ccfbef',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        chat: {
          bg:       '#f0f2f5',
          panel:    '#ffffff',
          sidebar:  '#ffffff',
          sent:     '#dcf8c6',
          received: '#ffffff',
          ia:       '#e8f5f0',
          header:   '#ffffff',
          input:    '#f0f2f5',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'message': '0 1px 2px rgba(0,0,0,0.08)',
        'panel': '0 1px 3px rgba(0,0,0,0.1)',
      }
    },
  },
  plugins: [],
}