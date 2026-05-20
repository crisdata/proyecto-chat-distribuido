// ListaContactos.jsx
// Panel central con la lista de contactos. Cada avatar tiene gradiente único.

import { useState, useEffect } from 'react'
import { Search, Bot, User, PenSquare } from 'lucide-react'
import { obtenerNoLeidos, formatearHora } from '../services/api'
import { getAvatarStyle } from '../utils/avatarColors'

export default function ListaContactos({
  contactos,
  contactoActivo,
  onSeleccionar,
  usuarioActual,
  iaId
}) {
  const [busqueda, setBusqueda] = useState('')
  const [noLeidos, setNoLeidos] = useState(0)

  useEffect(() => {
    if (!usuarioActual?.id) return

    async function actualizarNoLeidos() {
      try {
        const data = await obtenerNoLeidos(usuarioActual.id)
        setNoLeidos(data.no_leidos || 0)
      } catch {
        setNoLeidos(0)
      }
    }

    actualizarNoLeidos()
    const intervalo = setInterval(actualizarNoLeidos, 3000)
    return () => clearInterval(intervalo)
  }, [usuarioActual?.id])

  const contactosFiltrados = contactos.filter(c =>
    c.nombre.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div className="w-80 bg-vibe-900 border-r border-vibe-800 flex flex-col">

      <div className="px-5 pt-6 pb-4 border-b border-vibe-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-vibe-100">
            Mensajes
          </h2>
          {noLeidos > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-cyan-500
                             text-vibe-950 text-xs font-bold">
              {noLeidos > 9 ? '9+' : noLeidos}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 bg-vibe-800 rounded-xl
                        px-3 py-2.5 border border-vibe-700
                        focus-within:border-cyan-500 transition">
          <Search size={15} className="text-vibe-500 flex-shrink-0" />
          <input
            type="text"
            placeholder="Buscar conversaciones..."
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            className="flex-1 bg-transparent text-sm text-vibe-200
                       placeholder-vibe-500 outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {contactosFiltrados.length === 0 ? (
          <div className="flex flex-col items-center justify-center
                          h-40 text-vibe-500 text-sm gap-2">
            <User size={32} className="opacity-30" />
            <p>No hay contactos disponibles</p>
          </div>
        ) : (
          contactosFiltrados.map(contacto => {
            const esIA = contacto.id === iaId
            const activo = contactoActivo?.id === contacto.id

            return (
              <button
                key={contacto.id}
                onClick={() => onSeleccionar(contacto)}
                className={`w-full flex items-center gap-3 px-4 py-3
                            transition text-left border-b border-vibe-800/50
                            ${activo
                              ? esIA
                                ? 'bg-lumi-400/10 border-l-4 border-l-lumi-400'
                                : 'bg-cyan-500/10 border-l-4 border-l-cyan-500'
                              : 'hover:bg-vibe-800/50'
                            }`}
              >
                {/* Avatar con gradiente único por contacto */}
                <div
                  style={getAvatarStyle(contacto.nombre, esIA)}
                  className={`w-11 h-11 rounded-full flex items-center
                              justify-center flex-shrink-0 font-semibold
                              ${esIA ? 'text-white' : ''}`}
                >
                  {esIA
                    ? <Bot size={20} />
                    : contacto.nombre.charAt(0).toUpperCase()
                  }
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium truncate
                                      ${activo
                                        ? esIA ? 'text-lumi-400' : 'text-cyan-400'
                                        : 'text-vibe-200'
                                      }`}>
                      {contacto.nombre}
                    </span>
                    {contacto.creado_en && (
                      <span className="text-xs text-vibe-600 flex-shrink-0 ml-2">
                        {formatearHora(contacto.creado_en)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-vibe-500 truncate mt-0.5">
                    {esIA
                      ? 'Asistente de inteligencia artificial'
                      : 'Usuario registrado'
                    }
                  </p>
                </div>
              </button>
            )
          })
        )}
      </div>

      <div className="p-4 border-t border-vibe-800">
        <button className="w-full py-3 rounded-xl bg-gradient-vibe
                           text-white text-sm font-semibold transition
                           shadow-glow-cyan hover:opacity-90 active:scale-[0.98]
                           flex items-center justify-center gap-2">
          <PenSquare size={16} />
          Nuevo chat
        </button>
      </div>

    </div>
  )
}