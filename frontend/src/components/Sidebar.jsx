// Sidebar.jsx
// Panel izquierdo con navegación principal de Vibe.
// Estructura: Logo → Chats → Lumi (acceso rápido) → Configuración → Avatar
// Tema oscuro Privacy First con acentos cian (acciones) y púrpura (Lumi).

import { useState, useRef, useEffect } from 'react'
import { MessageCircle, Sparkles, Settings, LogOut } from 'lucide-react'

export default function Sidebar({
  usuario,
  contactos,
  iaId,
  onSeleccionar,
  onLogout
}) {
  // Estado del menú de configuración (abierto/cerrado)
  const [menuAbierto, setMenuAbierto] = useState(false)
  const menuRef = useRef(null)

  // Encuentra a Lumi en la lista de contactos para poder seleccionarla
  const lumi = contactos.find(c => c.id === iaId)

  // Cierra el menú al hacer click fuera
  useEffect(() => {
    function handleClickFuera(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuAbierto(false)
      }
    }
    if (menuAbierto) {
      document.addEventListener('mousedown', handleClickFuera)
      return () => document.removeEventListener('mousedown', handleClickFuera)
    }
  }, [menuAbierto])

  function abrirLumi() {
    if (lumi) onSeleccionar(lumi)
  }

  function confirmarLogout() {
    setMenuAbierto(false)
    onLogout()
  }

  return (
    <div className="w-20 bg-vibe-950 border-r border-vibe-800 flex flex-col
                    items-center py-6 gap-6 relative">

      {/* Logo Vibe */}
      <div className="w-11 h-11 rounded-xl bg-gradient-vibe flex items-center
                      justify-center shadow-glow-cyan">
        <MessageCircle size={22} className="text-white" />
      </div>

      {/* Separador */}
      <div className="w-8 h-px bg-vibe-800" />

      {/* Navegación */}
      <nav className="flex flex-col items-center gap-3 flex-1">

        {/* Chats — activo siempre por ahora (única vista del sistema) */}
        <button
          title="Chats"
          className="w-11 h-11 rounded-xl bg-cyan-500/15 text-cyan-400
                     flex items-center justify-center
                     hover:bg-cyan-500/25 transition"
        >
          <MessageCircle size={20} />
        </button>

        {/* Lumi — acceso rápido a la IA */}
        <button
          onClick={abrirLumi}
          disabled={!lumi}
          title="Chatear con Lumi"
          className="w-11 h-11 rounded-xl text-lumi-400
                     flex items-center justify-center
                     hover:bg-lumi-400/15 transition
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Sparkles size={20} />
        </button>

      </nav>

      {/* Configuración con menú flotante */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setMenuAbierto(!menuAbierto)}
          title="Configuración"
          className={`w-11 h-11 rounded-xl flex items-center justify-center transition
                      ${menuAbierto
                        ? 'bg-vibe-800 text-vibe-200'
                        : 'text-vibe-500 hover:bg-vibe-800 hover:text-vibe-300'}`}
        >
          <Settings size={20} />
        </button>

        {/* Popup del menú de configuración */}
        {menuAbierto && (
          <div className="absolute left-full ml-3 bottom-0
                          bg-vibe-900 border border-vibe-700 rounded-xl
                          shadow-panel p-4 w-56 z-50 animate-fade-in-up">

            {/* Info del usuario */}
            <div className="pb-3 mb-3 border-b border-vibe-800">
              <p className="text-xs text-vibe-500 mb-1">Sesión actual</p>
              <p className="text-sm font-medium text-vibe-100 truncate">
                {usuario?.nombre}
              </p>
            </div>

            {/* Botón cerrar sesión */}
            <button
              onClick={confirmarLogout}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                         text-sm text-red-400 hover:bg-red-500/10 transition"
            >
              <LogOut size={16} />
              <span>Cerrar sesión</span>
            </button>
          </div>
        )}
      </div>

      {/* Avatar del usuario actual (gradiente único viene en B2) */}
      <div
        title={usuario?.nombre}
        className="w-11 h-11 rounded-full bg-gradient-vibe flex items-center
                   justify-center text-white font-semibold text-base
                   cursor-default select-none"
      >
        {usuario?.nombre?.charAt(0).toUpperCase()}
      </div>

    </div>
  )
}