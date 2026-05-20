// Mensaje.jsx
// Burbuja individual de mensaje. Avatar del emisor con gradiente único.

import { Bot } from 'lucide-react'
import { formatearHora } from '../services/api'
import { getAvatarStyle } from '../utils/avatarColors'

export default function Mensaje({ mensaje, usuarioActual, iaId, nombreEmisor }) {
  const esEnviado = mensaje.emisor_id === usuarioActual.id
  const esIA = mensaje.emisor_id === iaId

  return (
    <div className={`flex items-end gap-2 mb-2 animate-fade-in-up
                     ${esEnviado ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar del remitente con gradiente único */}
      {!esEnviado && (
        <div
          style={getAvatarStyle(nombreEmisor, esIA)}
          className={`w-7 h-7 rounded-full flex items-center justify-center
                      flex-shrink-0 text-xs font-semibold mb-1
                      ${esIA ? 'text-white' : ''}`}
        >
          {esIA
            ? <Bot size={14} />
            : (nombreEmisor?.charAt(0).toUpperCase() || '?')
          }
        </div>
      )}

      {/* Burbuja del mensaje */}
      <div className={`max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl
                       shadow-bubble text-sm leading-relaxed
                       ${esEnviado
                         ? 'bg-gradient-vibe text-white rounded-br-sm'
                         : esIA
                           ? 'bg-vibe-700 text-vibe-100 rounded-bl-sm border-l-2 border-lumi-400'
                           : 'bg-vibe-700 text-vibe-100 rounded-bl-sm'
                       }`}>

        <p className="whitespace-pre-wrap break-words">
          {mensaje.contenido}
        </p>

        <p className={`text-xs mt-1 text-right
                       ${esEnviado
                         ? 'text-white/60'
                         : 'text-vibe-500'}`}>
          {formatearHora(mensaje.timestamp)}
        </p>
      </div>

    </div>
  )
}