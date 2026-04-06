// Sidebar.jsx
// Panel izquierdo con navegación principal.
// Usa lucide-react para íconos consistentes con el diseño minimalista.

import { MessageCircle, Circle, User, Settings } from 'lucide-react'

export default function Sidebar({ usuario }) {
  return (
    <div className="w-20 bg-white border-r border-gray-100 flex flex-col
                    items-center py-6 gap-6 shadow-panel">

      {/* Logo */}
      <div className="w-10 h-10 rounded-xl bg-primary-500 flex items-center
                      justify-center">
        <MessageCircle size={22} className="text-white" />
      </div>

      {/* Separador */}
      <div className="w-8 h-px bg-gray-100" />

      {/* Navegación */}
      <nav className="flex flex-col items-center gap-3 flex-1">

        {/* Chats — activo por defecto */}
        <button
          title="Chats"
          className="w-11 h-11 rounded-xl bg-primary-50 text-primary-500
                     flex items-center justify-center
                     hover:bg-primary-100 transition"
        >
          <MessageCircle size={20} />
        </button>

        {/* Estado */}
        <button
          title="Estado"
          className="w-11 h-11 rounded-xl text-gray-400
                     flex items-center justify-center
                     hover:bg-gray-100 transition"
        >
          <Circle size={20} />
        </button>

        {/* Perfil */}
        <button
          title="Perfil"
          className="w-11 h-11 rounded-xl text-gray-400
                     flex items-center justify-center
                     hover:bg-gray-100 transition"
        >
          <User size={20} />
        </button>

      </nav>

      {/* Configuración */}
      <button
        title="Configuración"
        className="w-11 h-11 rounded-xl text-gray-400
                   flex items-center justify-center
                   hover:bg-gray-100 transition"
      >
        <Settings size={20} />
      </button>

      {/* Avatar del usuario actual */}
      <div
        title={usuario?.nombre}
        className="w-11 h-11 rounded-full bg-primary-500 flex items-center
                   justify-center text-white font-semibold text-base
                   cursor-default select-none"
      >
        {usuario?.nombre?.charAt(0).toUpperCase()}
      </div>

    </div>
  )
}