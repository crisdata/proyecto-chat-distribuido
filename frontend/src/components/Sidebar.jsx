// Sidebar.jsx
// Panel izquierdo con navegación principal de Vibe.
// Avatar del usuario actual con gradiente único generado por hash del nombre.

import { useState, useRef, useEffect } from 'react'
import { MessageCircle, Sparkles, Settings, LogOut } from 'lucide-react'
import { getAvatarStyle } from '../utils/avatarColors'

export default function Sidebar({
  usuario,
  contactos,
  iaId,
  onSeleccionar,
  onLogout
}) {
  const [menuAbierto, setMenuAbierto] = useState(false)
  const menuRef = useRef(null)

  const lumi = contactos.find(c => c.id === iaId)

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

      <div className="w-8 h-px bg-vibe-800" />

      <nav className="flex flex-col items-center gap-3 flex-1">

        {/* Chats */}
        <button
          title="Chats"
          className="w-11 h-11 rounded-xl bg-cyan-500/15 text-cyan-400
                     flex items-center justify-center
                     hover:bg-cyan-500/25 transition"
        >
          <MessageCircle size={20} />
        </button>

        {/* Lumi */}
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

      {/* Configuración */}
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

        {menuAbierto && (
          <div className="absolute left-full ml-3 bottom-0
                          bg-vibe-900 border border-vibe-700 rounded-xl
                          shadow-panel p-4 w-56 z-50 animate-fade-in-up">

            <div className="pb-3 mb-3 border-b border-vibe-800">
              <p className="text-xs text-vibe-500 mb-1">Sesión actual</p>
              <p className="text-sm font-medium text-vibe-100 truncate">
                {usuario?.nombre}
              </p>
            </div>

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

      {/* Avatar del usuario actual — ahora con gradiente único */}
      <div
        title={usuario?.nombre}
        style={getAvatarStyle(usuario?.nombre)}
        className="w-11 h-11 rounded-full flex items-center justify-center
                   font-semibold text-base cursor-default select-none"
      >
        {usuario?.nombre?.charAt(0).toUpperCase()}
      </div>

    </div>
  )
}