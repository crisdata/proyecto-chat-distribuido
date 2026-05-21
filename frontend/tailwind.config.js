/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ─── Paleta Vibe — Privacy First ────────────────────────────────
        // Fondos escalonados: del más oscuro (vibe-950) al menos oscuro (vibe-700)
        // crean profundidad visual sin perder el carácter oscuro del producto.
        vibe: {
          950: '#0a0e1a',   // Fondo principal (chat, sidebar)
          900: '#0d1322',   // Fondo intermedio (lista de contactos)
          800: '#131a2c',   // Inputs, búsqueda
          700: '#1e293b',   // Burbujas recibidas
          600: '#334155',   // Bordes sutiles
          500: '#64748b',   // Texto secundario
          400: '#94a3b8',   // Texto medio
          300: '#cbd5e1',   // Texto principal en superficies
          200: '#e2e8f0',   // Texto principal en fondos oscuros
          100: '#f1f5f9',   // Texto destacado
        },
        // Cian eléctrico — color de acento principal (acciones, seguridad)
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',   // El cian "marca" de Vibe
          600: '#0891b2',
        },
        // Azul para gradientes en burbujas enviadas
        blue: {
          600: '#2563eb',
          700: '#1e40af',
        },
        // Púrpura — color exclusivo de Lumi (lo usamos en B3)
        lumi: {
          400: '#a855f7',
          500: '#9333ea',
          600: '#7e22ce',
        },
        // Verde para "en línea" (lo usamos en B4)
        online: {
          400: '#22c55e',
          500: '#16a34a',
        },
      },
      // Gradientes pre-definidos para uso fácil con clase `bg-gradient-...`
      backgroundImage: {
        'gradient-vibe': 'linear-gradient(135deg, #1e40af 0%, #06b6d4 100%)',
        'gradient-lumi': 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      // Sombras suaves para burbujas y paneles
      boxShadow: {
        'bubble': '0 1px 3px rgba(0,0,0,0.3)',
        'panel': '0 4px 12px rgba(0,0,0,0.4)',
        'glow-cyan': '0 0 20px rgba(6,182,212,0.3)',
        'glow-online': '0 0 6px rgba(52, 211, 153, 0.6)',
      },
      // Animaciones para mensajes que aparecen
      animation: {
        'fade-in-up': 'fadeInUp 0.3s ease-out',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}