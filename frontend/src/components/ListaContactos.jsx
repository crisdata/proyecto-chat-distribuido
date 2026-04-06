// ListaContactos.jsx
// Panel central con la lista de contactos disponibles.
// Muestra el indicador de mensajes no leídos del usuario actual.
// Distingue visualmente el nodo IA del resto de usuarios.

import { useState, useEffect } from 'react'
import { Search, Bot, User, PenSquare } from 'lucide-react'
import { obtenerNoLeidos, formatearHora } from '../services/api'

export default function ListaContactos({
  contactos,
  contactoActivo,
  onSeleccionar,
  usuarioActual,
  iaId
}) {
  const [busqueda, setBusqueda] = useState('')
  // Contador de mensajes no leídos del usuario actual
  const [noLeidos, setNoLeidos] = useState(0)

  // Consultar mensajes no leídos del usuario actual cada 3 segundos
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

  // Filtrar contactos según el texto de búsqueda
  const contactosFiltrados = contactos.filter(c =>
    c.nombre.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div className="w-80 bg-white border-r border-gray-100 flex flex-col">

      {/* Encabezado */}
      <div className="px-5 pt-6 pb-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">
            Mensajes
          </h2>
          {/* Indicador global de no leídos */}
          {noLeidos > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-primary-500
                             text-white text-xs font-bold">
              {noLeidos > 9 ? '9+' : noLeidos}
            </span>
          )}
        </div>

        {/* Buscador */}
        <div className="flex items-center gap-2 bg-gray-50 rounded-xl
                        px-3 py-2 border border-gray-100">
          <Search size={15} className="text-gray-400 flex-shrink-0" />
          <input
            type="text"
            placeholder="Buscar conversaciones..."
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            className="flex-1 bg-transparent text-sm text-gray-700
                       placeholder-gray-400 outline-none"
          />
        </div>
      </div>

      {/* Lista de contactos */}
      <div className="flex-1 overflow-y-auto py-2">
        {contactosFiltrados.length === 0 ? (
          <div className="flex flex-col items-center justify-center
                          h-40 text-gray-400 text-sm gap-2">
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
                            hover:bg-gray-50 transition text-left
                            border-b border-gray-50
                            ${activo
                              ? 'bg-primary-50 border-l-4 border-l-primary-500'
                              : ''
                            }`}
              >
                {/* Avatar */}
                <div className={`w-11 h-11 rounded-full flex items-center
                                 justify-center flex-shrink-0 text-white
                                 font-semibold
                                 ${esIA ? 'bg-emerald-500' : 'bg-primary-400'}`}>
                  {esIA
                    ? <Bot size={20} />
                    : contacto.nombre.charAt(0).toUpperCase()
                  }
                </div>

                {/* Información del contacto */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-medium truncate
                                      ${activo
                                        ? 'text-primary-600'
                                        : 'text-gray-800'
                                      }`}>
                      {contacto.nombre}
                    </span>
                    {contacto.creado_en && (
                      <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                        {formatearHora(contacto.creado_en)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 truncate mt-0.5">
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

      {/* Botón nuevo chat */}
      <div className="p-4 border-t border-gray-100">
        <button className="w-full py-2.5 rounded-xl bg-primary-500
                           hover:bg-primary-600 text-white text-sm
                           font-semibold transition flex items-center
                           justify-center gap-2">
          <PenSquare size={16} />
          Nuevo chat
        </button>
      </div>

    </div>
  )
}